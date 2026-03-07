.PHONY: reproduce reproduce-soft checksums

CHECKSUMS_OUT := checksums.txt

# Install dependencies, run the PULSE pack, and generate checksums.
# `reproduce` is strict/fail-closed.
reproduce:
	@echo "Installing dependencies..."
	python -m pip install --quiet -r requirements.txt
	@echo "Running PULSE pack to generate artefacts..."
	python PULSE_safe_pack_v0/tools/run_all.py
	@echo "Computing checksums..."
	@set -e; \
	tmp_file="$$(mktemp)"; \
	trap 'rm -f "$$tmp_file"' EXIT; \
	rm -f "$(CHECKSUMS_OUT)"; \
	python ./compute_checksums.py . > "$$tmp_file"; \
	mv "$$tmp_file" "$(CHECKSUMS_OUT)"
	@echo "Done. Artefacts and checksums are available in the current directory."

# Permissive local/demo variant that preserves the previous soft-fail behavior explicitly.
reproduce-soft:
	@echo "Installing dependencies..."
	python -m pip install --quiet -r requirements.txt
	@echo "Running PULSE pack to generate artefacts (soft mode)..."
	python PULSE_safe_pack_v0/tools/run_all.py || true
	@echo "Computing checksums..."
	@set -e; \
	tmp_file="$$(mktemp)"; \
	trap 'rm -f "$$tmp_file"' EXIT; \
	rm -f "$(CHECKSUMS_OUT)"; \
	python ./compute_checksums.py . > "$$tmp_file"; \
	mv "$$tmp_file" "$(CHECKSUMS_OUT)"
	@echo "Done. Artefacts and checksums are available in the current directory."

# Compute SHA-256 checksums for the current directory without hashing the manifest itself.
checksums:
	@set -e; \
	tmp_file="$$(mktemp)"; \
	trap 'rm -f "$$tmp_file"' EXIT; \
	rm -f "$(CHECKSUMS_OUT)"; \
	python ./compute_checksums.py . > "$$tmp_file"; \
	mv "$$tmp_file" "$(CHECKSUMS_OUT)"
