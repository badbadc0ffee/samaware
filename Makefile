SOURCE_DIR ?= src

.PHONY: lint

build: pyproject.toml $(SOURCE_DIR)
	python3 setup.py build

lint:
	ruff check $(SOURCE_DIR)
	# Also use pylint for now, until Ruff supports multi-file analysis
	pylint $(SOURCE_DIR)
