

git_remote_hg:  access hg repositories as git remotes
=====================================================

Are you a git junkie forced to work on projects hosted in mercurial repos?
Are you too lazy, stubborn or maladjusted to learn another VCS tool?
Fear not!  This script will let you interact with mercurial repositories as
if they were ordinary git remotes.

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

All the hard work of interoperating between git and mercurial is done by the
awesome hg-git module.  All the hard work of speaking the git-remote-helper
protocol is done by git's own http-protol handlers.  This script just hacks
them together to make it all work a little easier.

For each remote mercurial repository, you actually get *two* additional
repositories hidden inside your local git repo:

    * .git/hgremotes/[URL]:           a local hg clone of the remote repo
    * .git/hgremotes/[URL]/.hg/git:   a bare git repo managed by hg-git

Pushing from your local git repo into the remote mercurial repo goes like
this:

    * use git-remote-http to push into .git/hgremotes/[URL]/.hg/git
    * call "hg gimport" to import changes into .git/hgremotes/[URL]
    * call "hg push" to push them up to the remote repo

Likewise, pulling from the remote mercurial repo goes like this:

    * call "hg pull" to pull changes from the remote repo
    * call "hg gexport" to export them into .git/hgremotes/[URL]/.hg/git
    * use git-remote-http to pull them into your local repo

Ugly?  Sure.  Hacky?  You bet.  But it seems to work remarkably well.

There is apparently a native implementation of a git-remote-hg command in
development:

    https://plus.google.com/115991361267198418069/posts/Jpzi24bYU91

Since the git-remote-helper protocol is pretty simple, it should be possible
to switch back and forth between that implementation and this one without any
hassle.

THINGS TO DO:

    * I'm not clear exactly how mercurial bookmarks work.  hg-git seems to
      map them to git branches, but there are probaby some issues with how
      git-remote-hg exposes this to the user.  It *should* be possible for
      bookmarks to appear as multiple remote branches, but I don't need it
      so I haven't tried it.

