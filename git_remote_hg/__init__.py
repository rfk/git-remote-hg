"""

git_remote_hg:  access hg repositories as git remotes
=====================================================


"""

__ver_major__ = 0
__ver_minor__ = 1
__ver_patch__ = 0
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


def git_remote_hg(argv=None, git_dir=None):
    if argv is None:
        argv = sys.argv
    if git_dir is None:
        git_dir = os.getcwd()

    hg_url = argv[2]
    hg_checkout = HgGitCheckout(git_dir, hg_url)

    backend = GitHttpBackend(hg_checkout.git_repo_dir)
    t = backend.start()
    try:
        while backend.repo_url is None:
           time.sleep(0.1)

        hg_checkout.pull()
        cmd = ("git", "remote-http", backend.repo_url, )
        retcode = subprocess.call(cmd, env=os.environ)
        if retcode not in (0, 1):
            msg = "git-remote-http failed with error code %d" % (retcode,)
            raise RuntimeError(msg)
        hg_checkout.push()
    finally:
        backend.stop()
        t.join()


class HgGitCheckout(object):
    """Class managing a local hg-git checkout."""

    def __init__(self, git_dir, hg_url):
        self.hg_url = hg_url
        self.hg_name = hg_name = urllib.quote(hg_url, safe="")
        self.hg_repo_dir = os.path.join(git_dir, ".git", "hgremotes", hg_name)
        if not os.path.exists(self.hg_repo_dir):
            self.initialize_hg_repo()
        self.git_repo_dir = os.path.join(self.hg_repo_dir, ".hg", "git")

    def _do(self, *cmd, **kwds):
        kwds.setdefault("stdout", sys.stderr)
        return subprocess.check_call(cmd, **kwds)

    def pull(self):
        self._do("hg", "pull", cwd=self.hg_repo_dir)
        self._do("hg", "gexport", cwd=self.hg_repo_dir)

    def push(self):
        self._do("hg", "gimport", cwd=self.hg_repo_dir)
        self._do("hg", "push", cwd=self.hg_repo_dir)

    def initialize_hg_repo(self):
        print>>sys.stderr, "initializing hg repo from", self.hg_url
        hg_repo_dir = self.hg_repo_dir
        os.makedirs(os.path.dirname(hg_repo_dir))
        self._do("hg", "clone", self.hg_url, hg_repo_dir)
        self._do("hg", "update", "null", cwd=hg_repo_dir)
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
    """Run git-http-backend in a backend thread.

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
        t = threading.Thread(target=self.run)
        t.start()
        return t

    def stop(self):
        self.server.shutdown()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)

