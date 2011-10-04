

git_remote_hg:  access hg repositories as git remotes
=====================================================

Are you a git junkie forced to work on projects hosted in mercurial repos?
Are you too lazy, stubborn or maladjusted to learn another VCS tool?
Fear not!  This simple script will let you interact with mercurial repositories
as if they were ordinary git remotes.

Git allows pluggable remote repository protocols via helper scripts.  If you
have a script named "git-remote-XXX" then git will use it to interact with
remote repositories whose URLs are of the form XXX::some-url-here.  So you
can imagine what a script named git-remote-hg will do.

Yes, this script provides a remote repository protocol for communicating with 
mercurial.  Install it and you can do::

    $ git clone hg::https://hg.example.com/some-hg-repo
    $ cd some-hg-repo
    $ # hackety hackety hack
    $ git commit -a
    $ git push

The heavy lifting is done via the awesome hg-git module and git's own HTTP
HTTP protocol helpers - the code here just hacks them together to shuffle
bytes back and forth in the manner expected by a remote protocol helper.

Here's how it works:

    * use hg to take a local checkout, stored under.git/hgremotes/<URL>/ 
    * call `hg pull` and `hg gexport` on it, to pull in the latest
      changes from the mercurial repo.  We now have a matching git
      repo at .git/hgremotes/<URL>/.hg/git
    * spawn a local HTTP server that proxies to git-http-backend,
      serving repo at .git/hgremotes/<URL>/.hg/git
    * call git-remote-http and point it at this local server; this lets
      git push or pull to it as normal
    * call `hg gimport` to push the changes back into the local hg checkout
    * call `hg push` to send any changes back to mercurial.

Ugly?  Sure.  Hacky?  You bet.  But it seems to work remarkably well.


