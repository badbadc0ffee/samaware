SOURCE_DIR ?= src
TESTS_DIR ?= tests

.PHONY: build run test lint clean

build: pyproject.toml $(SOURCE_DIR)
	python3 -m build

run: src/samaware/static/samaware/vendor
	DJANGO_SETTINGS_MODULE=pretalx.settings django-admin runserver

test:
	DJANGO_SETTINGS_MODULE=pretalx.settings pytest $(TESTS_DIR)

lint:
	ruff check $(SOURCE_DIR) $(TESTS_DIR) setup_vendored.py
	# Also use pylint for now, until Ruff supports multi-file analysis
	pylint $(SOURCE_DIR) $(TESTS_DIR) setup_vendored.py

src/samaware/static/samaware/vendor:
	./setup_vendored.py

clean:
	rm -rf build dist src/samaware.egg-info
	rm -rf src/samaware/static/samaware/vendor
