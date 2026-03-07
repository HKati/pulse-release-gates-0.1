.PHONY: reproduce reproduce-soft checksums

# Install dependencies, run the PULSE pack, and generate checksums.
# `reproduce` is strict/fail-closed.
reproduce:
	@echo "Installing dependencies..."
	python -m pip install --quiet -r requirements.txt
	@echo "Running PULSE pack to generate artefacts..."
	python PULSE_safe_pack_v0/tools/run_all.py
	@echo "Computing checksums..."
	python ./compute_checksums.py . > checksums.txt
	@echo "Done. Artefacts and checksums are available in the current directory."

# Permissive local/demo variant that preserves the previous soft-fail behavior explicitly.
reproduce-soft:
	@echo "Installing dependencies..."
	python -m pip install --quiet -r requirements.txt
	@echo "Running PULSE pack to generate artefacts (soft mode)..."
	python PULSE_safe_pack_v0/tools/run_all.py || true
	@echo "Computing checksums..."
	python ./compute_checksums.py . > checksums.txt
	@echo "Done. Artefacts and checksums are available in the current directory."

# Compute SHA-256 checksums for the current directory using the repo-root tool.
checksums:
	python ./compute_checksums.py . > checksums.txt
