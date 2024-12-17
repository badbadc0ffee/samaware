SOURCE_DIR ?= src
TESTS_DIR ?= tests

.PHONY: run test lint

build: pyproject.toml $(SOURCE_DIR) src/samaware/static/samaware/vendor/htmx.min.js
	python3 setup.py build

run: src/samaware/static/samaware/vendor/htmx.min.js
	DJANGO_SETTINGS_MODULE=pretalx.settings django-admin runserver

test:
	DJANGO_SETTINGS_MODULE=pretalx.settings django-admin test $(TESTS_DIR)

lint:
	ruff check $(SOURCE_DIR) $(TESTS_DIR)
	# Also use pylint for now, until Ruff supports multi-file analysis
	pylint $(SOURCE_DIR) $(TESTS_DIR)

src/samaware/static/samaware/vendor:
	mkdir -p $@

src/samaware/static/samaware/vendor/htmx.min.js: src/samaware/static/samaware/vendor
	curl -L https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js -o $@
