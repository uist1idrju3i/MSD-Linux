# mksquashfs matrix repeat (B1)

prereg: docs/experiments/2026-11-15-storage-options-prereg.md (B1)
source tree: output-fscmp/target (~46MB), same as mksquashfs-quick-scan
runs: 3 repeats of run-mksquashfs-matrix.sh (matrix-r1..r3.csv) + medians (matrix-medians.csv)
note: image_bytes is deterministic per config (identical across repeats)
