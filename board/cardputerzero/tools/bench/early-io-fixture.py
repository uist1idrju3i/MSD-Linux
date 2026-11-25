#!/usr/bin/env python3
"""Prepare a separate QEMU-only early-I/O control fixture from an existing build."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[4]
MARKER_CONFIG = ['CONFIG_ASH=y', 'CONFIG_SH_IS_ASH=y', 'CONFIG_ASH_PRINTF=y',
                 'CONFIG_PRINTF=y', 'CONFIG_TRUE=y', 'CONFIG_TIMEOUT=y']


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def install_marker_commands(target, busybox, config, console):
    options = config.read_text().splitlines()
    for option in MARKER_CONFIG:
        if option not in options:
            raise ValueError('missing marker dependency: ' + option)
    for source in (busybox, console):
        if not source.is_file() or not os.access(source, os.X_OK):
            raise ValueError('missing executable marker dependency: ' + str(source))
    inputs = {}
    for relative, source in [('bin/busybox', busybox), ('usr/bin/msd-console', console)]:
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, path)
        inputs[relative] = digest(path)
    for relative in ['bin/sh', 'bin/true', 'usr/bin/printf', 'usr/bin/timeout']:
        path = target / relative
        if path.is_symlink() or path.exists():
            path.unlink()
        path.symlink_to(os.path.relpath(target / 'bin/busybox', path.parent))
    return inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--busybox', type=Path, help='Reuse a timeout-enabled BusyBox with its adjacent .config')
    parser.add_argument('--module-timeout', action='store_true', help='Inject a RAM-only fake DT and a sleeping modprobe before the real helper')
    args = parser.parse_args()
    build = args.build.resolve()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    images = destination / 'images'
    images.mkdir()
    target = destination / 'target'
    subprocess.run([str(build / 'host/bin/fakeroot'), str(build / 'host/bin/unsquashfs'), '-no-xattrs', '-d', str(target),
                    str(build / 'images/rootfs.squashfs')], check=True)
    paths = ['etc/init.d/S02a-msd-early-io', 'etc/init.d/S02msd-data',
             'etc/init.d/S04msd-keymap', 'usr/libexec/msd/early-io',
             'usr/libexec/msd/cardputer-keyboard', 'usr/sbin/msd-syncfs']
    inputs = {}
    for relative in paths:
        source = ROOT / 'board/cardputerzero/rootfs-overlay' / relative
        if not source.exists():
            source = build / 'target' / relative
        (target / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target / relative)
        inputs[relative] = digest(source)
    if args.busybox:
        busybox_binary = args.busybox.resolve()
        config = busybox_binary.with_name('.config')
    else:
        busybox_source = next((build / 'build').glob('busybox-*/Config.in')).parent
        busybox = destination / 'busybox'
        shutil.copytree(busybox_source, busybox, symlinks=True)
        config = busybox / '.config'
        text = config.read_text()
        if '# CONFIG_TIMEOUT is not set' in text:
            text = text.replace('# CONFIG_TIMEOUT is not set', 'CONFIG_TIMEOUT=y')
        elif 'CONFIG_TIMEOUT=y' not in text:
            raise ValueError('missing BusyBox timeout config')
        config.write_text(text)
        cross = str(build / 'host/bin/aarch64-linux-')
        subprocess.run(['make', '-C', str(busybox), 'oldconfig', 'CROSS_COMPILE=' + cross],
                       input=b'\n' * 1000, check=True)
        subprocess.run(['make', '-C', str(busybox), '-j2', 'CROSS_COMPILE=' + cross], check=True)
        busybox_binary = busybox / 'busybox'
    console_source = ROOT / 'package/msd-console/msd-console.c'
    console_binary = destination / 'msd-console'
    subprocess.run([str(build / 'host/bin/aarch64-linux-gcc'), '-Os', '-Wall', '-Wextra', '-Werror',
                    str(console_source), '-o', str(console_binary)], check=True)
    inputs.update(install_marker_commands(target, busybox_binary, config, console_binary))
    if args.module_timeout:
        wrapper = target / 'usr/libexec/msd/early-io-timeout-fixture'
        wrapper.write_text('''#!/bin/sh
set -eu
root=/run/msd-early-io-fixture
dt=$root/sys/firmware/devicetree/base
mkdir -p "$dt" "$root/run" "$root/proc" "$root/dev" "$root/bin" "$root/lib/firmware" "$root/usr/share/keymaps"
printf 'tmpfs /run tmpfs rw 0 0\\n' >"$root/proc/mounts"
: >"$root/proc/cmdline"
ln -s /proc/uptime "$root/proc/uptime"
ln -s /dev/kmsg "$root/dev/kmsg"
ln -s /dev/console "$root/dev/console"
if [ -c /dev/tty1 ]; then ln -s /dev/tty1 "$root/dev/tty1"; fi
for compatible in cardputerzero,st7789v_lcd m5stack,tca8418c m5stack,m5ioe1 m5stack,gpio-forwarder m5stack,pwm-backlight; do
    mkdir -p "$dt/$compatible"
    printf '%s\\000' "$compatible" >"$dt/$compatible/compatible"
done
printf fixture >"$root/lib/firmware/cardputerzero,st7789v_lcd.bin"
printf fixture >"$root/usr/share/keymaps/tca8418_keypad_m5stack_keymap.map"
printf '%s\\n' '#!/bin/sh' 'echo "<6>early-io-fixture: sleeping modprobe $1" >/dev/kmsg' 'exec sleep 30' >"$root/bin/modprobe"
chmod +x "$root/bin/modprobe"
export MSD_EARLY_IO_ROOT=$root MSD_EARLY_IO_TIMEOUT=3 PATH="$root/bin:$PATH"
exec /usr/libexec/msd/early-io "$@"
''')
        wrapper.chmod(0o755)
        init = target / 'etc/init.d/S02a-msd-early-io'
        init.write_text(init.read_text().replace('helper=/usr/libexec/msd/early-io',
                                              'helper=/usr/libexec/msd/early-io-timeout-fixture'))
    squashfs = images / 'rootfs.squashfs'
    mksquashfs = build / 'host/bin/mksquashfs.orig'
    if not mksquashfs.exists():
        mksquashfs = build / 'host/bin/mksquashfs'
    subprocess.run([str(mksquashfs), str(target), str(squashfs),
                    '-noappend', '-all-root', '-comp', 'xz', '-no-xattrs', '-processors', '2'], check=True)
    image = images / 'sdcard.img'
    shutil.copyfile(build / 'images/sdcard.img', image)
    table = json.loads(subprocess.check_output([str(build / 'host/sbin/sfdisk'), '-J', str(image)]))
    sectors = table['partitiontable']['sectorsize']
    with image.open('r+b') as disk:
        for number in (5, 6):
            part = table['partitiontable']['partitions'][number - 1]
            if squashfs.stat().st_size > part['size'] * sectors:
                raise ValueError('fixture rootfs exceeds slot')
            disk.seek(part['start'] * sectors)
            with squashfs.open('rb') as source:
                shutil.copyfileobj(source, disk)
    for name in ['Image', 'bcm2710-rpi-3-b.dtb', 'bcm2710-rpi-cm0.dtb']:
        shutil.copy2(build / 'images' / name, images / name)
    (destination / 'host').symlink_to(build / 'host', target_is_directory=True)
    record = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  description='Existing build with listed files and source-built msd-console in both slots; NOT a fresh product build or physical driver test',
                  base_build=str(build), source_overlay_hashes=inputs,
                  console_source_sha256=digest(console_source), marker_config_sha256=digest(config),
                  module_timeout_fixture=args.module_timeout,
                  base_images={name: digest(build / 'images' / name) for name in
                               ['Image', 'rootfs.squashfs', 'sdcard.img', 'bcm2710-rpi-3-b.dtb']},
                  fixture_images={p.name: digest(p) for p in images.iterdir()},
                  uid=os.getuid())
    (destination / 'fixture.json').write_text(json.dumps(record, indent=2) + '\n')
    print('QEMU early-I/O fixture: ' + str(destination))


if __name__ == '__main__':
    main()
