PYTHON ?= .venv/bin/python

.PHONY: clean sdist test format coverage coverage-html docs release

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .ruff_cache \
	       .hypothesis htmlcov .coverage coverage.xml site report.json
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

sdist:
	$(PYTHON) -m build --sdist

test:
	$(PYTHON) -m pytest -p no:warnings

format:
	$(PYTHON) -m ruff format src tests scripts
	$(PYTHON) -m ruff check --fix src tests scripts

coverage:
	$(PYTHON) -m coverage run -m pytest -p no:warnings
	$(PYTHON) -m coverage report -m

coverage-html:
	$(PYTHON) -m coverage run -m pytest -p no:warnings
	$(PYTHON) -m coverage html

docs:
	$(PYTHON) -m mkdocs build --strict

release: clean sdist
	$(PYTHON) -m build
	@echo "Artifacts built in dist/. Publish via the Release workflow."
