SPHINXOPTS ?=
SPHINXBUILD ?= sphinx-build
SOURCEDIR = docs
BUILDDIR = build
VENV = sphinxenv/bin/activate

run:
	. $(VENV); sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)"

spelling:
	. $(VENV); sphinx-build -b spelling "$(SOURCEDIR)" "$(BUILDDIR)"

install:
	@echo "... setting up virtualenv"
	python3 -m venv sphinxenv
	. $(VENV); pip install --upgrade -r requirements.txt

	@echo "\n" \
	"--------------------------------------------------------------- \n" \
	"* watch, build and serve the documentation: make run \n" \
	"* check spelling: make spelling \n" \
	"\n" \
	"enchant must be installed in order for pyenchant (and therefore \n" \
	"spelling checks) to work. \n" \
	"--------------------------------------------------------------- \n"
