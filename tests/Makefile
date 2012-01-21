VIRTUALENV_NAME = venv

ifdef $(WORKON_HOME)
VIRTUALENV_PATH = $(WORKON_HOME)/$(VIRTUALENV_NAME)
else
VIRTUALENV_PATH = ./$(VIRTUALENV_NAME)
endif

#### General

all: pycco_deps test_deps build

build: pycco_deps
	$(VIRTUALENV_PATH)/bin/pycco sockjs-protocol*.py

clean:
	rm -rf $(VIRTUALENV_PATH) *.pyc


#### Dependencies

venv:
ifdef WORKON_HOME
	mkvirtualenv $(VIRTUALENV_NAME)
else
	virtualenv $(VIRTUALENV_PATH)
endif

#-rm distribute-*.tar.gz || true

pycco_deps: venv/.pycco_deps
venv/.pycco_deps: venv
	$(VIRTUALENV_PATH)/bin/pip install pycco
	touch $(VIRTUALENV_PATH)/.pycco_deps

test_deps: venv/.test_deps
venv/.test_deps: venv
	pip install -r test_deps.txt
	touch $(VIRTUALENV_PATH)/.test_deps


#### Development

serve: pycco_deps
	@while [ 1 ]; do			\
		make build;			\
		sleep 0.1;			\
		inotifywait -r -q -e modify .;	\
	done


#### Deployment

upload: build
	@node -v > /dev/null
	[ -e ../sockjs-protocol-gh-pages ] || 				\
		git clone `git remote -v|tr "[:space:]" "\t"|cut -f 2`	\
			--branch gh-pages ../sockjs-protocol-gh-pages
	(cd ../sockjs-protocol-gh-pages; git pull;)
	cp docs/* ../sockjs-protocol-gh-pages
	(cd ../sockjs-protocol-gh-pages; git add pycco.css sockjs*html; git commit sockjs*html -m "Content regenerated";)
	(cd ../sockjs-protocol-gh-pages; node generate_index.js > index.html;)
	(cd ../sockjs-protocol-gh-pages; git add index.html; git commit index.html -m "Index regenerated";)
	@echo ' [*] Now run:'
	@echo '(cd ../sockjs-protocol-gh-pages; git push;)'
