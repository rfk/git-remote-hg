"""

git_remote_hg.test:  testcases for git_remote_hg
================================================


Actually there are no "tests" as such just yet.  This is simply here out of
habit, since I use it to sync the main docstring with README.rst.

"""

import os
import unittest

import git_remote_hg

class TestDocstring(unittest.TestCase):

    def test_readme_matches_docstring(self):
        """Ensure that the README is in sync with the docstring.

        This test should always pass; if the README is out of sync it just
        updates it with the contents of git_remote_hg.__doc__.
        """
        dirname = os.path.dirname
        readme = os.path.join(dirname(dirname(__file__)),"README.rst")
        if not os.path.isfile(readme):
            f = open(readme,"wb")
            f.write(git_remote_hg.__doc__.encode())
            f.close()
        else:
            f = open(readme,"rb")
            if f.read() != git_remote_hg.__doc__:
                f.close()
                f = open(readme,"wb")
                f.write(git_remote_hg.__doc__.encode())
                f.close()

