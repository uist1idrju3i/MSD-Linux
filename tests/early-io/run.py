#!/usr/bin/env python3
import ast
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
OVERLAY = REPO / 'board/cardputerzero/rootfs-overlay'
HELPER = OVERLAY / 'usr/libexec/msd/early-io'
MODULES = ['gpio-forwarder', 'm5ioe1', 'pwm_bl_m5stack', 'panel-mipi-dbi-m', 'tca8418_keypad_m5stack']
COMPATIBLES = ['cardputerzero,st7789v_lcd', 'm5stack,tca8418c', 'm5stack,m5ioe1',
               'm5stack,gpio-forwarder', 'm5stack,pwm-backlight']


class EarlyIO(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='msd-early-io-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.env = dict(os.environ, MSD_EARLY_IO_ROOT=str(self.root), MSD_EARLY_IO_TIMEOUT='2')
        self.env['PATH'] = str(self.root / 'bin') + ':' + os.environ['PATH']
        for p in ['run', 'dev/input', 'dev/dri', 'bin']:
            (self.root / p).mkdir(parents=True)
        self.write('proc/cmdline', '')
        self.write('proc/mounts', 'tmpfs /run tmpfs rw 0 0\n')
        self.write('sys/firmware/devicetree/base/compatible', 'raspberrypi,3-model-b\0brcm,bcm2837\0')
        self.link('/proc/uptime', 'proc/uptime')
        self.link('/dev/stderr', 'dev/kmsg')
        self.write('dev/console', '')
        self.script('modprobe', 'printf "%s\\n" "$1" >>"$MSD_EARLY_IO_ROOT/modules"\n'
                    '[ "${FAIL_MODULE:-}" != "$1" ] || exit 1\n'
                    '[ "${SLOW_MODULE:-}" != "$1" ] || exec sleep 10')
        self.script('loadkeys', 'echo loadkeys >>"$MSD_EARLY_IO_ROOT/modules"\nexit "${FAIL_KEYMAP:-0}"')
        helper = self.root / 'usr/libexec/msd/cardputer-keyboard'
        helper.parent.mkdir(parents=True)
        helper.write_bytes((OVERLAY / 'usr/libexec/msd/cardputer-keyboard').read_bytes())
        helper.chmod(0o755)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def link(self, target, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)

    def script(self, name, text):
        path = self.write('bin/' + name, '#!/bin/sh\n' + text + '\n')
        path.chmod(0o755)

    def physical(self):
        for index, compatible in enumerate(COMPATIBLES):
            self.write(f'sys/firmware/devicetree/base/device{index}/compatible', compatible + '\0')
        self.write('lib/firmware/cardputerzero,st7789v_lcd.bin', 'firmware')
        self.write('usr/share/keymaps/tca8418_keypad_m5stack_keymap.map', 'keymap')
        for bus, name, compatible, driver in [
            ('spi', 'panel', COMPATIBLES[0], 'panel-mipi-dbi-spi'),
            ('platform', 'light', COMPATIBLES[4], 'pwm-backlight'),
            ('i2c', 'keys', COMPATIBLES[1], 'tca8418_keypad'),
        ]:
            physical = self.root / f'sys/devices/{name}'
            self.write(f'sys/devices/{name}/of_node/compatible', compatible + '\0')
            driver_path = self.root / f'sys/bus/{bus}/drivers/{driver}'
            driver_path.mkdir(parents=True)
            self.link(driver_path, f'sys/devices/{name}/driver')
            self.link(physical, f'sys/bus/{bus}/devices/{name}')
        for target, class_path in [
            ('panel/drm/card2', 'drm/card2'),
            ('panel/graphics/fb1', 'graphics/fb1'),
            ('light/backlight/pwm', 'backlight/pwm'),
            ('keys/input/input3/event4', 'input/event4'),
        ]:
            path = self.root / 'sys/devices' / target
            path.mkdir(parents=True)
            self.link(path, 'sys/class/' + class_path)
        self.write('sys/devices/light/backlight/pwm/brightness', '100')
        self.write('sys/devices/keys/input/input3/name', 'tca8418c')
        self.link(self.root / 'sys/devices/keys/input/input3', 'sys/devices/keys/input/input3/event4/device')
        for node in ['dri/card2', 'fb1', 'input/event4', 'tty0']:
            self.link('/dev/null', 'dev/' + node)

    def run_helper(self, action='prepare'):
        result = subprocess.run([str(HELPER), action], env=self.env, capture_output=True,
                                text=True, timeout=5)
        self.assertTrue(result.stdout.isascii(), result.stdout)
        self.assertTrue(result.stderr.isascii(), result.stderr)
        return result

    def test_boot_scripts_use_english_only(self):
        for script in [HELPER, *(OVERLAY / 'etc/init.d').glob('S??*')]:
            for number, line in enumerate(script.read_text().splitlines(), 1):
                if not line.lstrip().startswith('#'):
                    self.assertTrue(line.isascii(), f'{script}:{number}: {line}')

    def state(self):
        return (self.root / 'run/msd-early-io/state').read_text().strip()

    def failed(self):
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertEqual(self.state(), 'failed')
        self.assertNotEqual(self.run_helper('gate').returncode, 0)

    def test_order_nodes_and_keymap(self):
        self.physical()
        result = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stderr)
        markers = ['early-io begin', 'LCD bound', 'keyboard ready', 'early-io end ready']
        offsets = [result.stderr.index(marker) for marker in markers]
        self.assertEqual(offsets, sorted(offsets))
        console = (self.root / 'dev/console').read_text()
        self.assertEqual([console.index(marker) for marker in markers], sorted(console.index(marker) for marker in markers))
        self.assertEqual(self.state(), 'ready')
        self.assertEqual((self.root / 'modules').read_text().splitlines(), MODULES + ['loadkeys'])
        self.assertEqual(self.run_helper('gate').returncode, 0)
        link = self.root / 'dev/input/cardputer-zero-internal'
        self.assertTrue(link.is_symlink())

    def test_qemu_absent_requires_explicit_flag(self):
        self.failed()
        self.write('proc/cmdline', 'msd.early_io=qemu')
        self.assertEqual(self.run_helper().returncode, 0)
        self.assertEqual(self.state(), 'hardware-absent-qemu')
        self.assertEqual(self.run_helper('gate').returncode, 0)
        self.assertFalse((self.root / 'modules').exists())

    def test_quiet_console_progress_does_not_depend_on_kernel_loglevel(self):
        self.physical()
        self.write('proc/cmdline', 'quiet')
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.set_blocking(master, False)
        self.link(os.ttyname(slave), 'dev/tty1')
        (self.root / 'dev/kmsg').unlink()
        self.write('dev/kmsg', '')
        self.env['MSD_EARLY_IO_TIMEOUT'] = '3'
        self.env['SLOW_MODULE'] = MODULES[0]
        result = self.run_helper()
        self.assertNotEqual(result.returncode, 0)
        console = (self.root / 'dev/console').read_text()
        fbcon = bytearray()
        deadline = time.monotonic() + 1
        while b'early-io end failed; boot blocked' not in fbcon:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([master], [], [], left)[0]:
                break
            fbcon.extend(os.read(master, 64))
        fbcon = fbcon.decode()
        for text in ['early-io begin', 'loading gpio-forwarder', 'waiting elapsed=',
                     'limit=3; safe to power off', 'early-io end failed; boot blocked']:
            self.assertIn(text, console)
            self.assertIn(text, fbcon)
            self.assertNotIn(text, result.stderr)
        self.assertEqual(self.state(), 'failed')

    def test_unknown_machine_and_partial_dt_are_not_absent(self):
        self.write('proc/cmdline', 'msd.early_io=qemu')
        self.write('sys/firmware/devicetree/base/compatible', 'unknown\0')
        self.failed()
        self.write('sys/firmware/devicetree/base/compatible', 'raspberrypi,3-model-b\0')
        self.write('sys/firmware/devicetree/base/lcd/compatible', COMPATIBLES[0] + '\0')
        self.failed()

    def test_s3_launcher_explicit_mode(self):
        source = REPO / 'board/cardputerzero/tools/bench/s3/s3-qemu.py'
        tree = ast.parse(source.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'qemu_command')
        namespace = dict(os=os, Path=Path, QEMU='qemu-system-aarch64',
                         args=SimpleNamespace(kernel='/kernel', dtb='/dtb'))
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
        for machine in ['raspi3b', 'raspi3ap']:
            for append in ['', 'msd.s3bench=1', 'msd.s3verify=1']:
                with self.subTest(machine=machine, append=append), patch.dict(
                        os.environ, QEMU_MACHINE=machine, QEMU_EXTRA_APPEND=''):
                    command = namespace['qemu_command']('/disk', '/log', append)
                    cmdline = command[command.index('-append') + 1]
                    self.assertEqual(cmdline.split().count('msd.early_io=qemu'), 1)
                    if append:
                        self.assertIn(append, cmdline.split())
                    self.write('proc/cmdline', cmdline)
                    self.assertEqual(self.run_helper().returncode, 0)
                    self.assertEqual(self.state(), 'hardware-absent-qemu')

    def test_duplicate_mode_rejected(self):
        self.write('proc/cmdline', 'msd.early_io=qemu msd.early_io=required')
        self.failed()

    def test_empty_and_duplicate_modes_reject_stale_qemu_state(self):
        for cmdline in ['', 'msd.early_io=', 'msd.early_io',
                        'msd.early_io=qemu msd.early_io=',
                        'msd.early_io= msd.early_io=qemu',
                        'msd.early_io=qemu msd.early_io= msd.early_io=',
                        'msd.early_io=qemu msd.early_io=qemu',
                        'msd.early_io=qemu msd.early_io',
                        'msd.early_io msd.early_io=qemu']:
            with self.subTest(cmdline=cmdline):
                self.write('proc/cmdline', cmdline + '\n')
                self.write('run/msd-early-io/state', 'hardware-absent-qemu\n')
                self.assertNotEqual(self.run_helper('gate').returncode, 0)
                self.failed()

    def test_each_module_failure(self):
        self.physical()
        for index, module in enumerate(MODULES):
            with self.subTest(module=module):
                self.env['FAIL_MODULE'] = module
                (self.root / 'modules').unlink(missing_ok=True)
                self.failed()
                self.assertEqual((self.root / 'modules').read_text().splitlines(), MODULES[:index + 1])

    def test_slow_module_deadline(self):
        self.physical()
        self.env['MSD_EARLY_IO_TIMEOUT'] = '1'
        self.env['SLOW_MODULE'] = MODULES[0]
        started = time.monotonic()
        self.failed()
        self.assertLess(time.monotonic() - started, 3)

    def test_missing_firmware(self):
        self.physical()
        (self.root / 'lib/firmware/cardputerzero,st7789v_lcd.bin').unlink()
        self.failed()
        self.assertFalse((self.root / 'modules').exists())

    def test_missing_bind(self):
        self.physical()
        (self.root / 'sys/devices/panel/driver').unlink()
        self.failed()

    def test_missing_input(self):
        self.physical()
        (self.root / 'dev/input/event4').unlink()
        self.failed()

    def test_missing_fb(self):
        self.physical()
        (self.root / 'dev/fb1').unlink()
        self.failed()

    def test_missing_drm(self):
        self.physical()
        (self.root / 'dev/dri/card2').unlink()
        self.failed()

    def test_missing_keymap(self):
        self.physical()
        (self.root / 'usr/share/keymaps/tca8418_keypad_m5stack_keymap.map').unlink()
        self.failed()

    def test_missing_backlight(self):
        self.physical()
        (self.root / 'sys/devices/light/backlight/pwm/brightness').unlink()
        self.failed()

    def test_bad_keymap_and_stale_ready(self):
        self.physical()
        self.assertEqual(self.run_helper().returncode, 0)
        self.env['FAIL_KEYMAP'] = '1'
        self.failed()

    def test_symlink_collision(self):
        self.physical()
        self.write('dev/input/cardputer-zero-internal', 'not a symlink')
        self.failed()

    def test_gate_missing_state_and_nonram(self):
        self.assertNotEqual(self.run_helper('gate').returncode, 0)
        self.write('proc/mounts', '/dev/mmcblk0p7 /run ext4 rw 0 0\n')
        self.assertNotEqual(self.run_helper().returncode, 0)
        self.assertFalse((self.root / 'run/msd-early-io').exists())

    def test_init_order_and_data_fail_closed(self):
        names = sorted(p.name for p in (OVERLAY / 'etc/init.d').glob('S??*'))
        self.assertLess(names.index('S02a-msd-early-io'), names.index('S02msd-data'))
        self.script('sleep', 'exec /bin/sleep 0.1')
        self.script('dd', 'echo bad >"$MSD_EARLY_IO_ROOT/data-touched"')
        for name in ['S02a-msd-early-io', 'S02msd-data']:
            with self.subTest(script=name):
                text = (OVERLAY / 'etc/init.d' / name).read_text()
                text = text.replace('/usr/libexec/msd/early-io', str(HELPER))
                path = self.write('init-test', text)
                process = subprocess.Popen(['sh', str(path)], env=self.env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           start_new_session=True)
                try:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        process.wait(timeout=0.3)
                    self.assertFalse((self.root / 'data-touched').exists())
                finally:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


if __name__ == '__main__':
    unittest.main()
