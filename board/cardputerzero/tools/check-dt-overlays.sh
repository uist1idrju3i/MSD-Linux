#!/bin/sh
set -eu

if [ "$#" -ne 3 ]; then
	printf 'Usage: %s <host-dir> <binaries-dir> <config.txt>\n' "$0" >&2
	exit 2
fi

HOST_DIR=$1
BINARIES_DIR=$2
CONFIG_FILE=$3
FDTOVERLAY="${HOST_DIR}/bin/fdtoverlay"
FDTGET="${HOST_DIR}/bin/fdtget"
BASE_DTB="${BINARIES_DIR}/bcm2710-rpi-cm0.dtb"
FIRMWARE_OVERLAYS="${BINARIES_DIR}/rpi-firmware/overlays"
M5_OVERLAYS="${BINARIES_DIR}/overlays"

for required in "$FDTOVERLAY" "$FDTGET" "$BASE_DTB" "$CONFIG_FILE"; do
	if [ ! -f "$required" ]; then
		printf 'Required device-tree input is missing: %s\n' "$required" >&2
		exit 1
	fi
done

TMP_DIR="$(mktemp -d "${BINARIES_DIR}/dt-overlays-check.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' 0 HUP INT TERM
CURRENT_DTB="${TMP_DIR}/current.dtb"
NEXT_DTB="${TMP_DIR}/next.dtb"
cp "$BASE_DTB" "$CURRENT_DTB"

apply_overlay() {
	overlay_name=$1
	case "$overlay_name" in
		''|*/*)
			printf 'Invalid device-tree overlay name: %s\n' "$overlay_name" >&2
			return 1
			;;
	esac

	if [ -f "${M5_OVERLAYS}/${overlay_name}.dtbo" ]; then
		overlay_file="${M5_OVERLAYS}/${overlay_name}.dtbo"
	elif [ -f "${FIRMWARE_OVERLAYS}/${overlay_name}.dtbo" ]; then
		overlay_file="${FIRMWARE_OVERLAYS}/${overlay_name}.dtbo"
	else
		printf 'Device-tree overlay not found: %s\n' "$overlay_name" >&2
		return 1
	fi

	printf 'Applying device-tree overlay: %s\n' "$overlay_name"
	if ! "$FDTOVERLAY" -i "$CURRENT_DTB" -o "$NEXT_DTB" "$overlay_file"; then
		printf 'Failed to apply device-tree overlay: %s\n' "$overlay_name" >&2
		return 1
	fi
	mv "$NEXT_DTB" "$CURRENT_DTB"
}

camera_overlay_configured=false
while IFS= read -r line || [ -n "$line" ]; do
	line="$(printf '%s\n' "$line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
	case "$line" in
		''|\#*) continue ;;
		dtoverlay=*)
			overlay_name="${line#dtoverlay=}"
			overlay_name="${overlay_name%%,*}"
			apply_overlay "$overlay_name"
			if [ "$overlay_name" = imx219 ]; then
				camera_overlay_configured=true
			fi
			;;
	esac
done <"$CONFIG_FILE"

CAMERA_DTB="$CURRENT_DTB"
if [ "$camera_overlay_configured" != true ]; then
	CAMERA_DTB="${TMP_DIR}/camera.dtb"
	cp "$CURRENT_DTB" "$CAMERA_DTB"
	CURRENT_DTB="$CAMERA_DTB"
	apply_overlay imx219
fi

find_imx219_node() {
	find_dtb=$1
	queue_file="${TMP_DIR}/node-queue"
	next_queue_file="${TMP_DIR}/node-queue-next"
	printf '/\n' >"$queue_file"

	while [ -s "$queue_file" ]; do
		find_path="$(sed -n '1p' "$queue_file")"
		sed '1d' "$queue_file" >"$next_queue_file"
		mv "$next_queue_file" "$queue_file"

		compatible="$("$FDTGET" -t s "$find_dtb" "$find_path" compatible 2>/dev/null || true)"
		case " ${compatible} " in
			*' sony,imx219 '*)
				printf '%s\n' "$find_path"
				return 0
				;;
		esac

		children="$("$FDTGET" -l "$find_dtb" "$find_path" 2>/dev/null || true)"
		while IFS= read -r child; do
			[ -n "$child" ] || continue
			if [ "$find_path" = / ]; then
				child_path="/${child}"
			else
				child_path="${find_path}/${child}"
			fi
			printf '%s\n' "$child_path" >>"$queue_file"
		done <<EOF
$children
EOF
	done
	return 1
}

if ! SENSOR_NODE="$(find_imx219_node "$CAMERA_DTB")"; then
	printf 'IMX219 node with compatible sony,imx219 was not found.\n' >&2
	exit 1
fi
SENSOR_STATUS="$("$FDTGET" -t s "$CAMERA_DTB" "$SENSOR_NODE" status 2>/dev/null || true)"
if [ "$SENSOR_STATUS" != okay ]; then
	printf 'IMX219 node is not enabled: %s status=%s\n' \
		"$SENSOR_NODE" "${SENSOR_STATUS:-<unset>}" >&2
	exit 1
fi

CSI1_STATUS="$("$FDTGET" -t s "$CAMERA_DTB" /soc/csi@7e801000 status 2>/dev/null || true)"
if [ "$CSI1_STATUS" != okay ]; then
	printf 'CSI1 is not enabled: /soc/csi@7e801000 status=%s\n' \
		"${CSI1_STATUS:-<unset>}" >&2
	exit 1
fi

printf 'Device-tree overlay check passed: IMX219 at %s; CSI1 status=%s\n' \
	"$SENSOR_NODE" "$CSI1_STATUS"
