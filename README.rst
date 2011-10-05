

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

