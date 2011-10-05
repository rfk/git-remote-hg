"""

git_remote_hg:  access hg repositories as git remotes
=====================================================

Are you a git junkie but need to work on projects hosted in mercurial repos?
Are you too stubborn, lazy or maladjusted to learn another VCS tool?  I
know I am.  But fear not!  This script will let you interact with mercurial
repositories as if they were ordinary git remotes.

Git allows pluggable remote repository protocols via helper scripts.  If you
have a script named "git-remote-XXX" then git will use it to interact with
remote repositories whose URLs are of the form XXX::some-url-here.  So you
can imagine what a script named git-remote-hg will do.

Yes, this script provides a remote repository implementation that communicates
with mercurial.  Install it and you can do::

    $ git clone hg::https://hg.example.com/some-mercurial-repo
    $ cd some-hg-repo
    $ # hackety hackety hack
    $ git commit -a
    $ git push

Tada!  Your commits from git will show up in the remote mercurial repo, and
none of your co-workers will be any the wiser.

All the hard work of interoperating between git and mercurial is done by the
awesome hg-git module.  All the hard work of speaking the git-remote-helper
protocol is done by git's own http-protocol handlers.  This script just hacks
them together to make it all work a little easier.

For each remote mercurial repository, you actually get *two* additional
repositories hidden inside your local git repo:

    * .git/hgremotes/[URL]:           a local hg clone of the remote repo
    * .git/hgremotes/[URL]/.hg/git:   a bare git repo managed by hg-git

When you "git push" from your local git repo into the remote mercurial repo,
here is what git-remote-hg will do for you:

    * use git-remote-http to push into .git/hgremotes/[URL]/.hg/git
    * call "hg gimport" to import changes into .git/hgremotes/[URL]
    * call "hg push" to push them up to the remote repo

Likewise, when you "git pull" from the remote mercurial repo into your local
git repo, here is what happens under the hood:

    * call "hg pull" to pull changes from the remote repo
    * call "hg gexport" to export them into .git/hgremotes/[URL]/.hg/git
    * use git-remote-http to pull them into your local repo

Ugly?  Sure.  Hacky?  You bet.  But it seems to work remarkably well.

By the way, there is apparently a native implementation of a git-remote-hg
command in development:

    https://plus.google.com/115991361267198418069/posts/Jpzi24bYU91

Since the git-remote-helper protocol is pretty simple, it should be possible
to switch back and forth between that implementation and this one without any
hassle.

WARNINGS:

    * Pushing multiple branches into the remote is currently broken.

      hg-git seems to map git branches onto mercurial bookmarks, but I'm not
      sure of all the details.  I don't need it so I haven't tried to make it
      work.  Don't do it.

"""

__ver_major__ = 0
__ver_minor__ = 1
__ver_patch__ = 1
__ver_sub__ = ""
__version__ = "%d.%d.%d%s" % (__ver_major__,__ver_minor__,__ver_patch__,__ver_sub__)


import sys
import os
import subprocess
import threading
import socket
import time
import urllib
import wsgiref.simple_server
from textwrap import dedent


def main(argv=None, git_dir=None):
    """Main entry-point for the git-remote-hg script.

    This function can be called to act as a git-remote-helper script that
    will communicate with a remote mercurial repository.  It basically does
    the following:

        * ensure there's a local hg checkout in .git/hgremotes/[URL]
        * ensure that it has a matching hg-git repo for import/export
        * update the hg-git repo from the remote mercurial repo
        * start a background thread running git-http-backend to communicate
          with the hg-git repo
        * shell out to hg-remote-http to push/pull into the hg-git repo
        * send any changes from the hg-git repo back to the remote

    Simple, right?
    """
    if argv is None:
        argv = sys.argv
    if git_dir is None:
        git_dir = os.environ.get("GIT_DIR", None)
    if git_dir is None:
        git_dir = os.getcwd()
        if os.path.exists(os.path.join(git_dir, ".git")):
            git_dir = os.path.join(git_dir, ".git")

    #  AFAICT, we always get the hg repo url as the second argument.
    hg_url = argv[2]

    #  Grab the local hg-git checkout, creating it if necessary.
    hg_checkout = HgGitCheckout(git_dir, hg_url)
    
    #  Start git-http-backend to push/pull into the hg-git checkout.
    backend = GitHttpBackend(hg_checkout.git_repo_dir)
    t = backend.start()
    try:
        #  Wait for the server to come up.
        while backend.repo_url is None:
           time.sleep(0.1)

        #  Grab any updates from the remote repo.
        #  Do it unconditionally for now, so we don't have to interpret
        #  the incoming hg-remote-helper stream to determine push/pull.
        hg_checkout.pull()

        #  Use git-remote-http to send all commands to the HTTP server.
        #  This will push any incoming changes into the hg-git checkout.
        cmd = ("git", "remote-http", backend.repo_url, )
        retcode = subprocess.call(cmd, env=os.environ)
        #  TODO: what are valid return codes?  Seems to be almost always 1.
        if retcode not in (0, 1):
            msg = "git-remote-http failed with error code %d" % (retcode,)
            raise RuntimeError(msg)

        #  If that worked OK, push any changes up to the remote URL.
        #  Do it unconditionally for now, so we don't have to interpret
        #  the incoming hg-remote-helper stream to determine push/pull.
        hg_checkout.push()
    finally:
        #  Make sure we tearn down the HTTP server before quitting.
        backend.stop()
        t.join()


class HgGitCheckout(object):
    """Class managing a local hg-git checkout.

    Given the path of a local git repository and the URL of a remote hg
    repository, this class manages a hidden hg-git checkout that can be
    used to shuffle changes between the two.
    """

    def __init__(self, git_dir, hg_url):
        self.hg_url = hg_url
        self.hg_name = hg_name = urllib.quote(hg_url, safe="")
        self.hg_repo_dir = os.path.join(git_dir, "hgremotes", hg_name)
        if not os.path.exists(self.hg_repo_dir):
            self.initialize_hg_repo()
        self.git_repo_dir = os.path.join(self.hg_repo_dir, ".hg", "git")

    def _do(self, *cmd, **kwds):
        """Run a hg command, capturing and reporting output."""
        silent = kwds.pop("silent", False)
        kwds["stdout"] = subprocess.PIPE
        kwds["stderr"] = subprocess.STDOUT
        p = subprocess.Popen(cmd, **kwds)
        output = p.stdout.readline()
        while output:
            if not silent:
                print>>sys.stderr, "hg: " + output.strip()
            output = p.stdout.readline()
        p.wait()

    def pull(self):
        """Grab any changes from the remote repository."""
        hg_repo_dir = self.hg_repo_dir
        self._do("hg", "pull", cwd=hg_repo_dir)
        self._do("hg", "bookmark", "-fr", "default", "master", cwd=hg_repo_dir)
        self._do("hg", "gexport", cwd=hg_repo_dir)

    def push(self):
        """Push any changes into the remote repository."""
        hg_repo_dir = self.hg_repo_dir
        self._do("hg", "gimport", cwd=hg_repo_dir)
        self._do("hg", "push", cwd=hg_repo_dir)

    def initialize_hg_repo(self):
        hg_repo_dir = self.hg_repo_dir
        if not os.path.isdir(os.path.dirname(hg_repo_dir)):
            os.makedirs(os.path.dirname(hg_repo_dir))
        self._do("hg", "clone", self.hg_url, hg_repo_dir)
        self._do("hg", "update", "null", cwd=hg_repo_dir, silent=True)
        with open(os.path.join(hg_repo_dir, "README.txt"), "wt") as f:
            f.write(dedent("""
            This is a bare mercurial checkout created by git-remote-hg.
            Don't mess with it unless you know what you're doing.
            """))
        with open(os.path.join(hg_repo_dir, ".hg", "hgrc"), "at") as f:
            f.write(dedent("""
            [extensions]
            hgext.bookmarks =
            hggit = 
            """))
        self._do("hg", "bookmark", "-r", "default", "master", cwd=hg_repo_dir)
        self._do("hg", "gexport", cwd=hg_repo_dir)


class SilentWSGIRequestHandler(wsgiref.simple_server.WSGIRequestHandler):
    """WSGIRequestHandler that doesn't print to stderr for each request."""
    def log_message(self, format, *args):
        pass


class GitHttpBackend(object):
    """Run git-http-backend in a background thread.

    This helper class lets us run the git-http-backend server in a background
    thread, bound to a local tcp port.  The main thread can then interact
    with it as needed.
    """

    def __init__(self, git_dir):
        self.git_dir = os.path.abspath(git_dir)
        self.git_project_root = os.path.dirname(self.git_dir)
        self.git_project_name = os.path.basename(self.git_dir)
        self.server = None
        self.server_url = None
        self.repo_url = None

    def __call__(self, environ, start_response):
        """WSGI handler.

        This simply sends all requests out to git-http-backend via
        standard CGI protocol.  It's nasty and inefficient but good
        enough for local use.
        """
        cgienv = os.environ.copy()
        for (k,v) in environ.iteritems():
            if isinstance(v, str):
                cgienv[k] = v
        cgienv["GIT_PROJECT_ROOT"] = self.git_project_root
        cgienv["GIT_HTTP_EXPORT_ALL"] = "ON"
        cgienv["REMOTE_USER"] = "rfk"
        cmd = ("git", "http-backend", )
        p = subprocess.Popen(cmd, env=cgienv, cwd=self.git_dir,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        if environ.get("CONTENT_LENGTH",None):
            data = environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"]))
            p.stdin.write(data)
        p.stdin.close()
        headers = []
        header = p.stdout.readline()
        while header.strip():
            headers.append(header.split(":", 1))
            header = p.stdout.readline()
        headers = [(k.strip(), v.strip()) for (k,v) in headers]
        start_response("200 OK", headers)
        return [p.stdout.read()]

    def _make_server(self, addr, port):
        make = wsgiref.simple_server.make_server
        return make(addr, port, self, handler_class=SilentWSGIRequestHandler)
                                                 
    def run(self):
        """Run the git-http-backend server."""
        port = 8091
        while True:
            try:
                self.server = self._make_server("localhost", port)
                break
            except socket.error:
                port += 1
        self.server_url = "http://localhost:%d/" % (port,)
        self.repo_url = self.server_url + self.git_project_name
        self.server.serve_forever()

    def start(self):
        """Run the git-http-backend server in a new thread."""
        t = threading.Thread(target=self.run)
        t.start()
        return t

    def stop(self):
        """Stop the git-http-backend server."""
        self.server.shutdown()


