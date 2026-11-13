"""Exercise release signing with throwaway keys and adversarial archives."""

import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
SIGN = ROOT / ".github/scripts/sign-update-bundle.sh"
BOARD = ROOT / "board/cardputerzero"


def command(*args, env=None, ok=True):
    result = subprocess.run([str(a) for a in args], env=env, capture_output=True)
    if (result.returncode == 0) != ok:
        raise AssertionError(f"Unexpected exit {result.returncode}: {args}\n"
                             + result.stdout.decode(errors="replace")
                             + result.stderr.decode(errors="replace"))
    return result.stdout


def put(path, data, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode() if isinstance(data, str) else data)
    if executable:
        path.chmod(0o755)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReleaseSigning(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.private = self.work / "private.pem"
        self.public = self.work / "public.pem"
        self.other = self.work / "other.pem"
        self.rsa = self.work / "rsa.pem"
        for key in (self.private, self.other):
            command("openssl", "genpkey", "-algorithm", "Ed25519", "-out", key)
        command("openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt",
                "rsa_keygen_bits:2048", "-out", self.rsa)
        command("openssl", "pkey", "-in", self.private, "-pubout", "-out", self.public)
        self.fingerprint = hashlib.sha256(command(
            "openssl", "pkey", "-pubin", "-in", self.public, "-outform", "DER")).hexdigest()
        self.members = {"rootfs.squashfs": b"rootfs fixture\n", "boot.vfat": b"boot fixture\n"}
        self.members["manifest"] = ("version 2\n" + "".join(
            f"{hashlib.sha256(data).hexdigest()}  {name}\n"
            for name, data in self.members.items())).encode()
        self.archive = self.work / "unsigned.tar"
        self.output = self.work / "signed.tar"
        self.pack()
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith("MSD_UPDATE_")}

    def pack(self, members=None, special=None):
        with tarfile.open(self.archive, "w") as archive:
            for name, data in (self.members if members is None else members).items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
            if special:
                archive.addfile(special)

    def sign(self, *, private=None, fingerprint=None, tar_hash=None, ok=True):
        command("bash", SIGN, self.archive, private or self.private, self.public,
                fingerprint or self.fingerprint, tar_hash or digest(self.archive),
                self.output, ok=ok)
        self.assertEqual(self.output.exists(), ok)

    def test_good_and_device_verification(self):
        self.sign()
        with tarfile.open(self.output) as archive:
            self.assertEqual(archive.getnames(),
                             ["rootfs.squashfs", "boot.vfat", "manifest", "manifest.sig"])
        dt = self.work / "dt"
        put(dt / "partition", (2).to_bytes(4, "big"))
        put(dt / "tryboot", bytes(4))
        put(self.work / "version", "1\n")
        for number in (3, 6):
            put(self.work / f"partition{number}", b"")
        put(self.work / "bin/fsync", "#!/bin/sh\nexit 0\n", True)
        env = dict(self.env, PATH=f"{self.work}/bin:{self.env['PATH']}",
                   MSD_UPDATE_DT_DIR=str(dt), MSD_UPDATE_KEY_PATH=str(self.public),
                   MSD_UPDATE_VERSION_PATH=str(self.work / "version"),
                   MSD_UPDATE_STATE_DIR=str(self.work / "state"),
                   MSD_UPDATE_PARTITION_PREFIX=str(self.work / "partition"))
        output = command("sh", BOARD / "rootfs-overlay/usr/sbin/msd-update",
                         "install", self.output, env=env)
        self.assertIn(b"Installed slot B", output)
        self.assertEqual((self.work / "partition6").read_bytes(), self.members["rootfs.squashfs"])
        self.assertEqual((self.work / "partition3").read_bytes(), self.members["boot.vfat"])

    def test_key_and_hash_failures(self):
        for key in (self.work / "missing.pem", self.rsa, self.other):
            with self.subTest(key=key.name):
                self.sign(private=key, ok=False)
        self.sign(fingerprint="0" * 64, ok=False)
        self.sign(tar_hash="0" * 64, ok=False)
        put(self.work / "empty.pem", "")
        self.sign(private=self.work / "empty.pem", ok=False)

    def test_tampered_files_and_manifest(self):
        for name in self.members:
            with self.subTest(member=name):
                changed = dict(self.members)
                changed[name] += b"tampered\n"
                self.pack(changed)
                self.sign(ok=False)
        for version in ("", "-1", "01", "1e3", "1" * 19):
            changed = dict(self.members)
            changed["manifest"] = self.members["manifest"].replace(b"version 2", f"version {version}".encode())
            self.pack(changed)
            self.sign(ok=False)

    def test_archive_members(self):
        for members in ({}, {k: v for k, v in self.members.items() if k != "boot.vfat"},
                        {**self.members, "extra": b"unexpected"}):
            self.pack(members)
            self.sign(ok=False)
        for name, kind in (("boot.vfat", tarfile.SYMTYPE), ("rootfs.squashfs", tarfile.LNKTYPE),
                           ("directory", tarfile.DIRTYPE), ("../escape", tarfile.REGTYPE),
                           ("/absolute", tarfile.REGTYPE), ("manifest", tarfile.REGTYPE)):
            special = tarfile.TarInfo(name)
            special.type = kind
            special.linkname = "/etc/passwd" if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ""
            members = dict(self.members)
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                members.pop(name)
            self.pack(members, special=special)
            self.sign(ok=False)
        self.archive.write_bytes(b"not a tar archive")
        self.sign(ok=False)

    def fixture(self):
        base = self.work / "build-output"
        target = base / "target"
        host = base / "host"
        source = (BOARD / "post-build.sh").read_text()
        required = re.search(r"required_target_commands='\n(.*?)\n'", source, re.S).group(1)
        for name in required.split():
            put(target / "usr/bin" / name, "#!/bin/sh\nexit 0\n", True)
        put(target / "etc/default/seedrng", 'SEEDRNG_ARGS="--seed-dir=/data/seedrng"\n')
        put(target / "etc/init.d/S01seedrng", "#!/bin/sh\nexit 0\n", True)
        put(target / "etc/init.d/S98msd-ready", "#!/bin/sh\nexit 0\n", True)
        put(target / "etc/init.d/S99msd-zram", "#!/bin/sh\nexit 0\n", True)
        put(target / "etc/fstab", "".join(f"none {p} tmpfs defaults 0 0\n"
                                         for p in ("/proc", "/sys", "/run", "/tmp")))
        put(target / "etc/mdev.conf", "$MODALIAS=.* 0:0 660 @modprobe\n")
        put(target / "usr/share/keymaps/tca8418_keypad_m5stack_keymap.map", "")
        put(base / "build/busybox-fixture/.config",
            "CONFIG_DESKTOP=y\nCONFIG_FEATURE_DD_IBS_OBS=y\nCONFIG_FEATURE_MD5_SHA1_SUM_CHECK=y\n"
            "CONFIG_FEATURE_SWAPON_PRI=y\n")
        for name in ("scripts/sign-file", "certs/signing_key.pem", "certs/signing_key.x509"):
            put(base / "build/linux-custom" / name, "")
        (target / "lib/modules").mkdir(parents=True)
        (host / "bin").mkdir(parents=True)
        (host / "bin/openssl").symlink_to(shutil.which("openssl"))
        self.base, self.target, self.host = base, target, host
        self.build_env = dict(self.env, BASE_DIR=str(base), HOST_DIR=str(host),
                              TARGET_DIR=str(target), MSD_UPDATE_PUBLIC_KEY=str(self.public))

    def post_build(self, ok=True):
        command("sh", BOARD / "post-build.sh", self.target, env=self.build_env, ok=ok)

    def test_post_build_public_and_both_keys(self):
        self.fixture()
        self.post_build()
        trust = self.target / "usr/share/msd-update"
        self.assertEqual((trust / "update-key.pem").read_bytes(), self.public.read_bytes())
        self.assertEqual((trust / "key-origin").read_text(), "release\n")
        self.assertFalse((self.base / "msd-update-dev-key.pem").exists())
        self.build_env["MSD_UPDATE_SIGNING_KEY"] = str(self.other)
        self.post_build(ok=False)
        self.build_env["MSD_UPDATE_SIGNING_KEY"] = str(self.private)
        self.post_build()
        self.build_env["MSD_UPDATE_PUBLIC_KEY"] = str(self.work / "missing-public.pem")
        self.post_build(ok=False)
        self.build_env["MSD_UPDATE_PUBLIC_KEY"] = str(self.rsa)
        self.post_build(ok=False)
        self.build_env["MSD_UPDATE_PUBLIC_KEY"] = str(self.private)
        self.post_build(ok=False)

    def test_development_and_private_compatibility(self):
        self.fixture()
        self.build_env.pop("MSD_UPDATE_PUBLIC_KEY")
        self.post_build()
        self.assertTrue((self.base / "msd-update-dev-key.pem").is_file())
        self.assertEqual((self.target / "usr/share/msd-update/key-origin").read_text(), "development\n")
        self.build_env["MSD_UPDATE_SIGNING_KEY"] = str(self.private)
        self.post_build()
        self.assertEqual((self.target / "usr/share/msd-update/update-key.pem").read_bytes(),
                         self.public.read_bytes())
        self.assertEqual((self.target / "usr/share/msd-update/key-origin").read_text(), "release\n")

    def test_post_image_unsigned_only_and_signed_compatibility(self):
        self.fixture()
        self.post_build()
        images = self.base / "images"
        for name in ("Image", "bcm2710-rpi-cm0.dtb", "bcm2710-rpi-3-b.dtb", "rootfs.squashfs",
                     "rpi-firmware/bootcode.bin", "rpi-firmware/start_cd.elf",
                     "rpi-firmware/fixup_cd.dat"):
            put(images / name, "fixture\n")
        put(images / "rpi-firmware/config.txt", "")
        (images / "rpi-firmware/overlays").mkdir()
        for name in ("fdtoverlay", "fdtget"):
            (self.host / "bin" / name).symlink_to(shutil.which("true"))
        put(self.host / "bin/pigz", '#!/bin/sh\nshift\nexec gzip "$@"\n', True)
        put(self.host / "bin/genimage",
            '#!/usr/bin/env python3\nimport pathlib,sys\n'
            'p=pathlib.Path(sys.argv[sys.argv.index("--outputpath")+1])\n'
            '(p/"boot.vfat").write_bytes(b"boot fixture\\n")\n'
            '(p/"sdcard.img").write_bytes(b"sd fixture\\n")\n', True)
        env = dict(self.build_env, BINARIES_DIR=str(images),
                   PATH=f"{self.host}/bin:{self.env['PATH']}")
        put(images / "msd-update-bundle.tar", "stale signed artifact")
        command("bash", BOARD / "post-image.sh", env=env)
        self.assertFalse((images / "msd-update-bundle.tar").exists())
        with tarfile.open(images / "msd-update-bundle.unsigned.tar") as archive:
            self.assertEqual(archive.getnames(), ["rootfs.squashfs", "boot.vfat", "manifest"])
        for path in images.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"PRIVATE KEY", path.read_bytes())
                self.assertNotEqual(path.suffix, ".pem")
        env["MSD_UPDATE_SIGNING_KEY"] = str(self.private)
        command("bash", BOARD / "post-image.sh", env=env)
        self.assertFalse((images / "msd-update-bundle.unsigned.tar").exists())
        with tarfile.open(images / "msd-update-bundle.tar") as archive:
            self.assertEqual(archive.getnames(),
                             ["rootfs.squashfs", "boot.vfat", "manifest", "manifest.sig"])

    def test_committed_fingerprint_and_workflow_guards(self):
        public = BOARD / "keys/release-1-public.pem"
        expected = "ec181b24375d93e884e05888d8348900fd1bc6405e225696716dc9feeb7f1f42"
        actual = hashlib.sha256(command("openssl", "pkey", "-pubin", "-in", public,
                                        "-outform", "DER")).hexdigest()
        self.assertEqual(actual, expected)
        command("bash", SIGN, self.archive, self.private, public, expected,
                digest(self.archive), self.output, ok=False)
        self.assertFalse(self.output.exists())
        workflow = (ROOT / ".github/workflows/release-sign.yml").read_text()
        build, sign = workflow.split("\n  sign:\n")
        self.assertEqual(workflow.count("if: github.ref == 'refs/heads/main'"), 2)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("secrets.", build)
        self.assertNotIn("environment:", build)
        self.assertIn("environment: release-signing", sign)
        self.assertIn("secrets.MSD_RELEASE_ED25519_PRIVATE_KEY_PEM", sign)
        self.assertIn(expected, sign)
        self.assertIn("if: always()\n        run: rm -f", sign)
        self.assertIn("BEGIN ([A-Z0-9]+ )?PRIVATE KEY", sign)

    def test_docker_forwards_only_the_public_key_input(self):
        put(self.work / "bin/docker",
            "#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n", True)
        env = dict(self.env, PATH=f"{self.work}/bin:{self.env['PATH']}",
                   MSD_DEV_ROOTLESS="1", MSD_UPDATE_PUBLIC_KEY="/work/public.pem",
                   MSD_UPDATE_SIGNING_KEY="/private-key-must-not-be-forwarded.pem")
        output = command("bash", ROOT / "docker/msd-dev", "true", env=env)
        self.assertIn(b"MSD_UPDATE_PUBLIC_KEY=/work/public.pem", output)
        self.assertNotIn(b"MSD_UPDATE_SIGNING_KEY", output)
        self.assertNotIn(b"private-key-must-not-be-forwarded", output)

    def test_workflow_build_fails_closed(self):
        workflow = (ROOT / ".github/workflows/release-sign.yml").read_text()
        build = workflow.split("      - name: Build with the committed public key\n", 1)[1]
        build = build.split("\n      - ", 1)[0]
        inner = build.split("docker/msd-dev bash -c '", 1)[1].rsplit("'", 1)[0]
        self.assertIn("set -euo pipefail", inner)
        put(self.work / "bin/make", '#!/bin/sh\nexit "$MOCK_MAKE_STATUS"\n', True)
        put(self.work / "bin/xz", '#!/bin/sh\ntouch "$UNEXPECTED_PACKAGE"\n', True)
        marker = self.work / "unexpected-package"
        env = dict(self.env, PATH=f"{self.work}/bin:{self.env['PATH']}",
                   UNEXPECTED_PACKAGE=str(marker))
        for prefix, status in (("", "31"), ("test() { return 1; }\n", "0")):
            command("bash", "-c", prefix + inner,
                    env=dict(env, MOCK_MAKE_STATUS=status), ok=False)
            self.assertFalse(marker.exists())

    def test_workflow_sign_cleanup_and_leak_checks(self):
        workflow = (ROOT / ".github/workflows/release-sign.yml").read_text()

        def script(name):
            body = workflow.split(f"      - name: {name}\n", 1)[1].split("\n      - ", 1)[0]
            return textwrap.dedent(body.split("        run: |\n", 1)[1])

        payload = self.work / "release-payload"
        payload.mkdir()
        shutil.copyfile(self.archive, payload / "msd-update-bundle.unsigned.tar")
        put(payload / "COMMIT", "fixture-commit\n")
        signing = script("Sign the validated manifest").replace(
            "board/cardputerzero/keys/release-1-public.pem", str(self.public)).replace(
            "ec181b24375d93e884e05888d8348900fd1bc6405e225696716dc9feeb7f1f42",
            self.fingerprint)
        env = dict(self.env, RUNNER_TEMP=str(self.work),
                   RELEASE_PRIVATE_KEY=self.private.read_text(), UNSIGNED_SHA256=digest(self.archive))
        command("bash", "-euo", "pipefail", "-c", signing, env=env)
        self.assertEqual((self.work / "msd-release-private.pem").stat().st_mode & 0o777, 0o600)
        cleanup = workflow.split("      - name: Remove the private key\n", 1)[1].split("\n      - ", 1)[0]
        cleanup = cleanup.split("        run: ", 1)[1]
        command("bash", "-euo", "pipefail", "-c", cleanup, env=env)
        self.assertFalse((self.work / "msd-release-private.pem").exists())
        scan = script("Check outputs for private keys")
        command("bash", "-euo", "pipefail", "-c", scan, env=env)
        put(payload / "leaked.pem", "")
        command("bash", "-euo", "pipefail", "-c", scan, env=env, ok=False)
        (payload / "leaked.pem").unlink()
        put(payload / "leak.txt", self.private.read_bytes())
        command("bash", "-euo", "pipefail", "-c", scan, env=env, ok=False)
        (payload / "leak.txt").unlink()
        missing = dict(env, RELEASE_PRIVATE_KEY="")
        command("bash", "-euo", "pipefail", "-c", signing, env=missing, ok=False)
        command("bash", "-euo", "pipefail", "-c", cleanup, env=missing)
        self.assertFalse((self.work / "msd-release-private.pem").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
