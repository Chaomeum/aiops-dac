PYTHON := .venv/bin/python
MODEL := model/architecture.yml
VALIDATOR := tools/validate.py
PHYSICAL_GENERATOR := tools/generators/physical.py
DOMAIN_MODEL := model/domain.yml
DESIGN_MODEL := model/design.yml
# Expose the already installed NVM exporter to environment checks as well.
DBML_TOOL_BIN := $(shell $(PYTHON) -c 'import sys; sys.path.insert(0, "tools/generators"); from domain_model import find_tool; print(find_tool("dbml2sql").parent)' 2>/dev/null)
export PATH := $(DBML_TOOL_BIN):$(PATH)

.PHONY: all check-env validate validate-domain validate_design validate-logical-expo classes physical logical logical-expo c4 db dbml sql er dictionary clean

all: check-env validate physical logical logical-expo c4 db classes

check-env:
	@PYTHON="$(PYTHON)" bash tools/check_env.sh

validate:
	@echo "==> Validating architecture model"
	@$(PYTHON) $(VALIDATOR) $(MODEL) $(DOMAIN_MODEL)

validate-domain: validate
	@$(PYTHON) tools/domain_validation.py $(DOMAIN_MODEL) $(MODEL)

validate_design: validate
	@$(PYTHON) tools/validate_design.py $(DESIGN_MODEL) $(MODEL) $(DOMAIN_MODEL)

classes: validate_design
	@echo "==> Generating proposed class diagrams (PlantUML)"
	@$(PYTHON) tools/generators/classes.py $(DESIGN_MODEL) $(MODEL) $(DOMAIN_MODEL)

db: dictionary

dbml: validate-domain
	@$(PYTHON) tools/generators/to_dbml.py

sql: dbml
	@$(PYTHON) tools/generators/to_sql.py

er: sql
	@$(PYTHON) tools/generators/to_er_d2.py

dictionary: er
	@$(PYTHON) tools/generators/to_dictionary.py

physical: validate
	@echo "==> Generating physical views"
	@$(PYTHON) tools/run_legacy_views.py $(PHYSICAL_GENERATOR)

logical: validate
	@echo "==> Generating logical architecture (D2 + ELK)"
	@$(PYTHON) tools/run_legacy_views.py tools/generators/logical.py

validate-logical-expo: validate
	@$(PYTHON) tools/generators/logical_presentation.py --validate-only

logical-expo: validate-logical-expo
	@echo "==> Generating logical presentation views (Graphviz)"
	@$(PYTHON) tools/generators/logical_presentation.py

c4: validate
	@echo "==> Generating C4 architecture"
	@$(PYTHON) tools/generators/c4.py

clean:
	@echo "==> Cleaning generated artifacts"
	@find build -mindepth 1 -maxdepth 1 -type f -delete
	@find out -mindepth 1 -maxdepth 1 -type f -delete
