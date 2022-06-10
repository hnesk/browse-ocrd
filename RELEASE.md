
# Make a new release

1) Review commits at https://github.com/hnesk/browse-ocrd/compare/v0.5.1...master and put noteworthy changes into the [CHANGELOG](CHANGELOG.md) 
2) Update `__version__` in [`__init__.py`](ocrd_browser/__init__.py)
3) `git commit` 
4) `git tag -a v0.5.1` 
5) `git push`
6) `git push --tags`
7) https://github.com/hnesk/browse-ocrd/releases/new and paste CHANGELOG changes
8) `make testpypi`
9) `make pypi`
