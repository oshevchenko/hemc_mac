.PHONY: build utestpypi upypi clean veryclean test install freeze init irun run

# Makefile for hemc_mac project
MAKEFILE_PATH := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SRC_PATH ?= $(MAKEFILE_PATH)/src
VENV_PATH ?= $(MAKEFILE_PATH)/venv
VENV_BIN_PATH = $(VENV_PATH)/bin

$(VENV_BIN_PATH)/python3:
	python3 -m venv $(VENV_PATH)

init:
	$(VENV_BIN_PATH)/python3 -m pip install -r requirements-all.txt

build:
	$(VENV_BIN_PATH)/python3 -m build

utestpypi:
	$(VENV_BIN_PATH)/python3 -m twine upload --repository testpypi dist/* --verbose

upypi:
	$(VENV_BIN_PATH)/python3 -m twine upload dist/*

irun:
	@echo "To install hemc_mac run 'make build install'"
	$(VENV_BIN_PATH)/python3 -m hemc_mac

run:
	@echo "Run from the src directory ${SRC_PATH}"
	cd $(SRC_PATH) && \
	$(VENV_BIN_PATH)/python3 -m hemc_mac --credentials $(MAKEFILE_PATH)/credentials.txt

clean:
	rm -rf dist

veryclean: clean
	rm -rf $(VENV_PATH)

test:
	$(VENV_BIN_PATH)/python3 -m unittest discover -s tests

install:
	$(VENV_BIN_PATH)/python3 -m pip install --force-reinstall dist/*.whl

freeze:
	$(VENV_BIN_PATH)/python3 -m pip freeze > requirements.txt
	$(VENV_BIN_PATH)/python3 -m pip freeze --local > requirements-local.txt
	$(VENV_BIN_PATH)/python3 -m pip freeze --user > requirements-user.txt
	$(VENV_BIN_PATH)/python3 -m pip freeze --all > requirements-all.txt

build utestpypi upypi test install freeze init irun run: $(VENV_PATH)/bin/python3
