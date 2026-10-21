# S21 sysctl and ramoops test tools

These scripts build test-only rootfs/SD variants and collect the S21 results.
They do not modify the product overlay, defconfig, kernel fragment, or product
cmdline.

Set `OUTPUT_DIR` to a Buildroot output for this checkout, and set
`S21_LOG_ROOT` to a persistent directory outside the repository. The preregistered
matrix is fixed at five trials per condition (one Y1 A/B trial):

```sh
LOG_ROOT="$HOME/work/s21-logs"
OUTPUT_DIR="$HOME/work/qemu-watchdog/output"
VARIANTS="$LOG_ROOT/variants"
POWERFAIL_REPO="$HOME/work/s21-powerfail-runner"

git worktree add --detach "$POWERFAIL_REPO" "$(git rev-parse HEAD)"

for variant in Y0 Y1 Y2 P0 R0; do
  board/cardputerzero/tools/bench/sysctl-ramoops/make-variant.sh \
    "$variant" "$OUTPUT_DIR" "$VARIANTS/$variant"
done
S21_SHARED_ROOTFS="$VARIANTS/P0/rootfs.squashfs" \
  board/cardputerzero/tools/bench/sysctl-ramoops/make-variant.sh \
  P1 "$OUTPUT_DIR" "$VARIANTS/P1"
S21_SHARED_ROOTFS="$VARIANTS/R0/rootfs.squashfs" \
  board/cardputerzero/tools/bench/sysctl-ramoops/make-variant.sh \
  R1 "$OUTPUT_DIR" "$VARIANTS/R1"

OUTPUT_DIR="$OUTPUT_DIR" QEMU_LOG_DIR="$LOG_ROOT" docker/msd-dev \
  board/cardputerzero/tools/bench/sysctl-ramoops/make-ramoops-dtb.sh \
  "$OUTPUT_DIR/images/bcm2710-rpi-cm0.dtb" "$VARIANTS/R1/ramoops.dtb"

OUTPUT_DIR="$OUTPUT_DIR" S21_LOG_ROOT="$LOG_ROOT" \
  S21_VARIANT_ROOT="$VARIANTS" \
  board/cardputerzero/tools/bench/sysctl-ramoops/run-sysctl.sh

S21_POWERFAIL_REPO="$POWERFAIL_REPO" \
  OUTPUT_DIR="$OUTPUT_DIR" S21_LOG_ROOT="$LOG_ROOT" \
  S21_VARIANT_ROOT="$VARIANTS" \
  board/cardputerzero/tools/bench/sysctl-ramoops/run-powerfail.sh

OUTPUT_DIR="$OUTPUT_DIR" QEMU_LOG_DIR="$LOG_ROOT" docker/msd-dev \
  board/cardputerzero/tools/bench/sysctl-ramoops/run-panic.sh

board/cardputerzero/tools/bench/sysctl-ramoops/analyze-results.py \
  docs/experiments/2026-10-21-s21-qemu-sysctl-ramoops.csv --all-columns
```

`run-powerfail.sh` calls the existing `test-powerfail.sh` unchanged in an
isolated worktree. It supplies each variant through `POWERFAIL_IMAGE`; the
staging output tree exposes that variant's rootfs to the existing integrity
template builder. P0/P1 share the P0 rootfs, and R0/R1 share the R0 rootfs, so
the panic and ramoops comparisons change only the preregistered conditions.
The one-second spacing between invocations only ensures that
the unchanged script's second-resolution run IDs remain unique.

`run-panic.sh` runs inside `msd-dev`, keeps a per-trial SD card copy under the
log root, and waits up to 120 seconds for the second boot to reach ready. The
R1 device tree is decompiled and compiled by Buildroot's `dtc` from inside the
same container.

For amended replacement sets, select the fixed five-trial condition with
distinct run IDs:

```sh
OUTPUT_DIR="$OUTPUT_DIR" QEMU_LOG_DIR="$LOG_ROOT" docker/msd-dev \
  board/cardputerzero/tools/bench/sysctl-ramoops/run-panic.sh \
  --modes R1 --run-tag amendment3 \
  --variant-root "$LOG_ROOT/variants-amendment3"
OUTPUT_DIR="$OUTPUT_DIR" QEMU_LOG_DIR="$LOG_ROOT" docker/msd-dev \
  board/cardputerzero/tools/bench/sysctl-ramoops/run-panic.sh \
  --modes P0 --run-tag amendment2 --variant-root "$VARIANTS"
```

The R1 runner waits for `s21: pstore collection complete` after second-boot
ready before it terminates QEMU, and removes NUL bytes from the serial log
before parsing pstore records. Before starting, it refuses any run whose log
directory or CSV run ID already exists.
