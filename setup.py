#
#  This is the git-remote-hg setuptools script.
#  Originally developed by Ryan Kelly, 2011.
#
#  This script is placed in the public domain.
#

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

#  Extract the docstring and version declaration from the module.
#  To avoid errors due to missing dependencies or bad python versions,
#  we explicitly read the file contents up to the end of the version
#  delcaration, then exec it ourselves.
info = {}
src = open("git_remote_hg/__init__.py")
lines = []
for ln in src:
    lines.append(ln)
    if "__version__" in ln:
        for ln in src:
            if "__version__" not in ln:
                break
            lines.append(ln)
        break
exec("".join(lines),info)


NAME = "git-remote-hg"
VERSION = info["__version__"]
DESCRIPTION = "access hg repositories as git remotes"
LONG_DESC = info["__doc__"]
AUTHOR = "Ryan Kelly"
AUTHOR_EMAIL = "ryan@rfk.id.au"
URL="http://packages.python.org/git-remote-hg"
LICENSE = "MIT"
KEYWORDS = "git hg mercurial"
SCRIPTS = ["scripts/git-remote-hg"]
INSTALL_REQUIRES = ["hg-git"]
CLASSIFIERS = [
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.5",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "License :: OSI Approved",
    "License :: OSI Approved :: MIT License",
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
]

setup(name=NAME,
      version=VERSION,
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      url=URL,
      description=DESCRIPTION,
      long_description=LONG_DESC,
      license=LICENSE,
      keywords=KEYWORDS,
      packages=["git_remote_hg"],
      scripts=SCRIPTS,
      install_requires=INSTALL_REQUIRES,
      classifiers=CLASSIFIERS
     )

