.PHONY: reproduce checksums

# Install dependencies, run the PULSE pack and generate checksums. Adjust paths as necessary
reproduce:
	@echo "Installing dependencies..."
	python -m pip install --quiet -r requirements.txt
	@echo "Running PULSE pack to generate artefacts..."
	python PULSE_safe_pack_v0/tools/run_all.py || true
	@echo "Computing checksums..."
	python tools/compute_checksums.py . > checksums.txt
	@echo "Done. Artefacts and checksums are available in the current directory."

# Compute SHA‑256 checksums of all files under the given directory (default: current directory)
checksums:
	python tools/compute_checksums.py . > checksums.txt