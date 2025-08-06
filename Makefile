.PHONY: venv build utestpypi upypi clean veryclean test install freeze


VENV_PATH ?= venv
VENV_BIN_PATH = $(VENV_PATH)/bin

$(VENV_PATH)/bin/python3: requirements.txt
	@if [ ! -f "$(VENV_PATH)/bin/python3" ]; then \
		echo "Creating virtual environment at $(VENV_PATH)"; \
		python3 -m venv $(VENV_PATH); \
		$(VENV_BIN_PATH)/python3 -m pip install --upgrade pip; \
		$(VENV_BIN_PATH)/python3 -m pip install -r requirements.txt; \
		$(VENV_BIN_PATH)/python3 -m pip install --upgrade build; \
		$(VENV_BIN_PATH)/python3 -m pip install --upgrade twine; \
	else \
		echo "Virtual environment already exists at $(VENV_PATH)"; \
	fi

requirements.txt:
	@echo "Generating requirements.txt"
	@echo "Please ensure you have a valid requirements.txt file before running this Makefile."
	@echo "You can create it by running 'make freeze' in your project directory."
	python3 -m pip freeze > requirements.txt

build:
	rm -rf dist
	$(VENV_BIN_PATH)/python3 -m build

utestpypi:
	$(VENV_BIN_PATH)/python3 -m twine upload --repository testpypi dist/* --verbose

upypi:
	$(VENV_BIN_PATH)/python3 -m twine upload dist/*

clean:
	rm -rf dist

veryclean: clean
	rm -rf $(VENV_PATH)

test:
	$(VENV_BIN_PATH)/python3 -m unittest discover -s tests

install:
	$(VENV_BIN_PATH)/python3 -m pip install --force-reinstall dist/*.whl
	$(VENV_BIN_PATH)/python3 -m pip install --force-reinstall dist/*.whl

freeze:
	$(VENV_BIN_PATH)/python3 -m pip freeze > requirements.txt
	$(VENV_BIN_PATH)/python3 -m pip freeze --local > requirements-local.txt
	$(VENV_BIN_PATH)/python3 -m pip freeze --user > requirements-user.txt
	$(VENV_BIN_PATH)/python3 -m pip freeze --all > requirements-all.txt

test install utestpypi upypi build freeze veryclean: $(VENV_PATH)/bin/python3
