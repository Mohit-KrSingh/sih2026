.PHONY: up down test lint seed demo rules-doc

ifeq ($(OS),Windows_NT)
  SHELL := powershell.exe
  .SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
  UP_CMD := .\scripts\up.ps1
  DOWN_CMD := .\scripts\down.ps1
  TEST_CMD := .\scripts\test.ps1
  LINT_CMD := .\scripts\lint.ps1
  SEED_CMD := .\scripts\seed.ps1
  DEMO_CMD := .\scripts\demo.ps1
  RULES_DOC_CMD := .\scripts\rules_doc.ps1
else
  UP_CMD := ./scripts/up.sh
  DOWN_CMD := ./scripts/down.sh
  TEST_CMD := ./scripts/test.sh
  LINT_CMD := ./scripts/lint.sh
  SEED_CMD := ./scripts/seed.sh
  DEMO_CMD := ./scripts/demo.sh
  RULES_DOC_CMD := ./scripts/rules_doc.sh
endif

up:
	$(UP_CMD)

down:
	$(DOWN_CMD)

test:
	$(TEST_CMD)

lint:
	$(LINT_CMD)

seed:
	$(SEED_CMD)

demo:
	$(DEMO_CMD)

rules-doc:
	$(RULES_DOC_CMD)
