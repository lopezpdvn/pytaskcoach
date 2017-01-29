GITHUB_REMOTE	=	origin
GITHUB_PUSH_BRANCHS	=	master
TESTS_DIR = pytaskcoach/tests/
TESTS_FP_PREFIX = test_*
PYTHON = python3

.PHONY: help

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  test         Run unit tests"
	@echo "  push         Push selected branches to GitHub repository"

test:
	@$(PYTHON) -m unittest discover -v -s $(TESTS_DIR) -p $(TESTS_FP_PREFIX)

push:
	git push $(GITHUB_REMOTE) $(GITHUB_PUSH_BRANCHS)
