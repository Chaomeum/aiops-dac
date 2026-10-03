PYTHON := .venv/bin/python
MODEL := model/architecture.yml
VALIDATOR := tools/validate.py

.PHONY: all check-env validate clean

all: check-env validate

check-env:
	@bash tools/check_env.sh

validate:
	@echo "==> Validating architecture model"
	@$(PYTHON) $(VALIDATOR) $(MODEL)

clean:
	@echo "==> Cleaning generated artifacts"
	@find build -mindepth 1 -maxdepth 1 -type f -delete
	@find out -mindepth 1 -maxdepth 1 -type f -delete