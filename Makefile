.PHONY: reproduce reproduce-soft checksums

PYTHON ?= python
CHECKSUMS_OUT ?= checksums.txt

# Install dependencies, run the PULSE pack, and generate checksums.
# `reproduce` is strict/fail-closed.
reproduce:
	@echo "Installing dependencies..."
	$(PYTHON) -m pip install --quiet -r requirements.txt
	@echo "Running PULSE pack to generate artefacts..."
	$(PYTHON) PULSE_safe_pack_v0/tools/run_all.py
	@$(MAKE) --no-print-directory checksums
	@echo "Done. Artefacts and checksums are available in the current directory."

# Permissive local/demo variant that keeps soft-fail behavior explicit.
reproduce-soft:
	@echo "Installing dependencies..."
	$(PYTHON) -m pip install --quiet -r requirements.txt
	@echo "Running PULSE pack to generate artefacts (soft mode)..."
	-$(PYTHON) PULSE_safe_pack_v0/tools/run_all.py
	@$(MAKE) --no-print-directory checksums
	@echo "Done. Artefacts and checksums are available in the current directory."

# Compute SHA-256 checksums of top-level files under the current directory
# without hashing the output manifest itself.
checksums:
	@echo "Computing checksums..."
	@set -e; \
	tmp_file="$$(mktemp)"; \
	trap 'rm -f "$$tmp_file"' EXIT; \
	rm -f "$(CHECKSUMS_OUT)"; \
	$(PYTHON) ./compute_checksums.py . > "$$tmp_file"; \
	mv "$$tmp_file" "$(CHECKSUMS_OUT)"
