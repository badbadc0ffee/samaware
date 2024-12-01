SOURCE_DIR ?= src
TESTS_DIR ?= tests

.PHONY: run test lint

build: pyproject.toml $(SOURCE_DIR)
	python3 setup.py build

run:
	DJANGO_SETTINGS_MODULE=pretalx.settings django-admin runserver

test:
	DJANGO_SETTINGS_MODULE=pretalx.settings django-admin test $(TESTS_DIR)

lint:
	ruff check $(SOURCE_DIR) $(TESTS_DIR)
	# Also use pylint for now, until Ruff supports multi-file analysis
	pylint $(SOURCE_DIR) $(TESTS_DIR)
