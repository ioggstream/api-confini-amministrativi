#
# Generate a browser bundle
#
#
TMPDIR := $(shell mktemp  -u /tmp/fooXXXXXX)
# $(shell git config --get remote.origin.url)

ifndef CIRCLE_REPOSITORY_URL
	REPO_ORIGIN := "."
else
	REPO_ORIGIN := $(CIRCLE_REPOSITORY_URL)
endif

all: process

# Create the web pages in bundle/
process: setup
	poetry run ./generate-geojson.py


gh-pages: process
	git clone $(REPO_ORIGIN) $(TMPDIR) -b gh-pages
	mv build/* $(TMPDIR)
	git -C $(TMPDIR) add .
	git -C $(TMPDIR) -c user.name="gh-pages bot" -c user.email="gh-bot@example.it" \
		commit -m "Script updating gh-pages from $(shell git rev-parse --short HEAD). [ci skip]"
	git -C $(TMPDIR) push -q origin gh-pages
	rm $(TMPDIR) -fr

setup:
	pip install poetry

clean:
	# removing compiled bundle and node_modules
	rm -rf build

