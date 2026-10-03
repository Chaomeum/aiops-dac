PYTHON := .venv/bin/python
MODEL := model/architecture.yml
VALIDATOR := tools/validate.py
PHYSICAL_GENERATOR := tools/generators/physical.py

.PHONY: all check-env validate physical logical clean

all: check-env validate physical logical

check-env:
	@PYTHON="$(PYTHON)" bash tools/check_env.sh

validate:
	@echo "==> Validating architecture model"
	@$(PYTHON) $(VALIDATOR) $(MODEL)

physical: validate
	@echo "==> Generating physical views"
	@$(PYTHON) $(PHYSICAL_GENERATOR)

logical: validate
	@echo "==> Generating logical architecture (D2 + ELK)"
	@$(PYTHON) tools/generators/logical.py

clean:
	@echo "==> Cleaning generated artifacts"
	@find build -mindepth 1 -maxdepth 1 -type f -delete
	@find out -mindepth 1 -maxdepth 1 -type f -delete