#!/usr/bin/env python3
"""Check that public_html/ contains only the local, script-free GitHub Pages site."""

from __future__ import annotations

import argparse
import html.parser
import os
import posixpath
import re
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


SITE_ORIGIN = "https://muromi.moe"
SITE_ORIGIN_HOST = urlsplit(SITE_ORIGIN).hostname or ""
FIXED_SITE_PATHS = {
    "public_html/index.html",
    "public_html/404.html",
    "public_html/site.css",
}
IMAGE_PATH_RE = re.compile(r"public_html/images/[^/]+\.(?:svg|png|webp)\Z")
LOGO_FILES = (
    "msd-linux-logo.svg",
    "msd-linux-logo-dark.svg",
    "msd-linux-mark.svg",
)
SOCIAL_WEBP = "public_html/images/msd-linux-social-1280x640.webp"
SOCIAL_WEBP_URL = f"{SITE_ORIGIN}/images/msd-linux-social-1280x640.webp"
REQUIRED_IMAGES = (
    "flow-light.svg",
    "flow-dark.svg",
    "seigaiha-light.svg",
    "seigaiha-dark.svg",
)
CSP_DEFAULT_RE = re.compile(r"(?:^|;)\s*default-src\s+'none'\s*(?:;|$)", re.IGNORECASE)
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_URL_RE = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*?))\s*\)""", re.IGNORECASE)
SITE_PATTERNS = "docs/logo/tools/site_patterns.py"


class Reporter:
    def __init__(self) -> None:
        self.errors = 0
        self.files = 0
        self.references_checked = 0

    def error(self, path: str, line: int, message: str) -> None:
        print(f"{path}:{line}: error: {message}")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            safe_path = (
                path.replace("%", "%25")
                .replace("\r", "%0D")
                .replace("\n", "%0A")
                .replace(",", "%2C")
            )
            safe_message = (
                message.replace("%", "%25")
                .replace("\r", "%0D")
                .replace("\n", "%0A")
            )
            print(f"::error file={safe_path},line={line}::{safe_message}")
        self.errors += 1

    def summary(self) -> None:
        print(
            "Summary: "
            f"files={self.files} "
            f"references_checked={self.references_checked} "
            f"errors={self.errors}"
        )


@dataclass(frozen=True)
class MetadataURL:
    path: str
    line: int
    kind: str
    value: str | None


def tracked_paths(root: Path, pathspec: str | None = None) -> set[str]:
    command = ["git", "-C", str(root), "ls-files", "-z"]
    if pathspec is not None:
        command.extend(("--", pathspec))
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or "git ls-files failed")
    return {
        os.fsdecode(item).replace(os.sep, "/")
        for item in result.stdout.split(b"\0")
        if item
    }


def read_bytes(root: Path, path: str, reporter: Reporter) -> bytes | None:
    full_path = root / path
    try:
        if not full_path.is_file() or full_path.is_symlink():
            reporter.error(path, 1, "通常のファイルではありません")
            return None
        return full_path.read_bytes()
    except OSError as exc:
        reporter.error(path, 1, f"ファイルを読み込めません: {exc}")
        return None


def read_text(root: Path, path: str, reporter: Reporter) -> str | None:
    raw = read_bytes(root, path, reporter)
    if raw is None:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        line = raw[: exc.start].count(b"\n") + 1
        reporter.error(path, line, "UTF-8 ではありません")
        return None
    reporter.files += 1
    return text


def check_site_allowlist(site_paths: set[str], reporter: Reporter) -> None:
    for path in sorted(site_paths):
        if path not in FIXED_SITE_PATHS and not IMAGE_PATH_RE.fullmatch(path):
            reporter.error(
                path,
                1,
                "public_html/ はサイト専用です。文書は docs/ に置いてください。",
            )
    for path in sorted(FIXED_SITE_PATHS - site_paths):
        reporter.error(path, 1, "必要なサイトファイルが追跡されていません")


def check_expected_pages_cname(value: str, reporter: Reporter) -> None:
    host = value.strip()
    if not host:
        reporter.error("Pages", 1, "Pages の Settings にドメインがありません")
    elif host.casefold() != SITE_ORIGIN_HOST.casefold():
        reporter.error(
            "Pages",
            1,
            f"Pages の Settings のドメインが SITE_ORIGIN ({SITE_ORIGIN_HOST}) と一致しません",
        )


def resolve_local_target(source_path: str, value: str) -> tuple[str | None, str | None]:
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return None, "URL の形式が不正です"
    if parts.scheme or parts.netloc:
        return None, "外部リソースを参照できません"

    target_path = unquote(parts.path)
    if "\\" in target_path or "\0" in target_path:
        return None, "参照先の path に不正な文字があります"
    if target_path == "":
        target = source_path
    elif target_path == "/":
        target = "public_html/index.html"
    elif target_path.startswith("/"):
        target = posixpath.normpath(
            posixpath.join("public_html", target_path.lstrip("/"))
        )
    else:
        target = posixpath.normpath(
            posixpath.join(posixpath.dirname(source_path), target_path)
        )
    if not target.startswith("public_html/"):
        return None, "参照先が public_html/ の外です"
    return target, None


def check_local_reference(
    source_path: str,
    line: int,
    value: str,
    site_paths: set[str],
    reporter: Reporter,
) -> None:
    reporter.references_checked += 1
    target, problem = resolve_local_target(source_path, value)
    if problem:
        reporter.error(source_path, line, f"{problem}: {value}")
    elif target not in site_paths:
        reporter.error(
            source_path,
            line,
            f"public_html/ 内の追跡ファイルが見つかりません: {value}",
        )


def check_metadata_url(
    metadata: MetadataURL,
    site_paths: set[str],
    reporter: Reporter,
) -> None:
    value = metadata.value
    if value is None or not value.strip():
        reporter.error(metadata.path, metadata.line, f"{metadata.kind} URL が空です")
        return
    try:
        parts = urlsplit(value.strip())
        port = parts.port
    except ValueError:
        reporter.error(metadata.path, metadata.line, f"{metadata.kind} URL の形式が不正です")
        return

    if not parts.scheme and not parts.netloc:
        reporter.error(
            metadata.path,
            metadata.line,
            f"{metadata.kind} URL は HTTPS の SITE_ORIGIN ({SITE_ORIGIN}) を使ってください",
        )
        return

    if (
        parts.scheme.lower() != "https"
        or not parts.netloc
        or not parts.hostname
        or parts.hostname.casefold() != SITE_ORIGIN_HOST.casefold()
        or parts.netloc.casefold() != SITE_ORIGIN_HOST.casefold()
        or port is not None
    ):
        reporter.error(
            metadata.path,
            metadata.line,
            f"{metadata.kind} URL の host と scheme は SITE_ORIGIN ({SITE_ORIGIN}) に一致させてください",
        )
    if metadata.kind == "og:image":
        image_path = parts.path or "/"
        check_local_reference(
            metadata.path, metadata.line, image_path, site_paths, reporter
        )


def srcset_urls(value: str) -> list[str]:
    urls = []
    for candidate in value.split(","):
        fields = candidate.strip().split()
        if fields:
            urls.append(fields[0])
    return urls


class SiteHTMLParser(html.parser.HTMLParser):
    def __init__(
        self,
        path: str,
        site_paths: set[str],
        reporter: Reporter,
    ) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.site_paths = site_paths
        self.reporter = reporter
        self.csp_lines: list[tuple[int, str | None]] = []
        self.metadata_urls: list[MetadataURL] = []
        self.metadata_properties: dict[str, list[tuple[int, str | None]]] = {}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        line = self.getpos()[0]
        attributes: dict[str, str | None] = {}
        for name, value in attrs:
            if name is not None:
                attributes.setdefault(name.lower(), value)
            if name and len(name) > 2 and name.lower().startswith("on"):
                self.reporter.error(self.path, line, "on* イベント属性は禁止です")
            if name and name.lower() == "style":
                self.reporter.error(self.path, line, "style 属性は禁止です")

        if tag == "script":
            self.reporter.error(self.path, line, "script 要素は禁止です")
        if tag == "style":
            self.reporter.error(self.path, line, "style 要素は禁止です")

        rel = (attributes.get("rel") or "").lower().split()
        is_canonical = tag == "link" and "canonical" in rel
        if tag == "meta":
            http_equiv = (attributes.get("http-equiv") or "").lower()
            if http_equiv == "content-security-policy":
                self.csp_lines.append((line, attributes.get("content")))
            property_name = (attributes.get("property") or "").lower()
            if property_name:
                self.metadata_properties.setdefault(property_name, []).append(
                    (line, attributes.get("content"))
                )
            if property_name in {"og:url", "og:image"}:
                self.metadata_urls.append(
                    MetadataURL(
                        self.path,
                        line,
                        property_name,
                        attributes.get("content"),
                    )
                )
        if is_canonical:
            self.metadata_urls.append(
                MetadataURL(
                    self.path,
                    line,
                    "canonical",
                    attributes.get("href"),
                )
            )

        for name in ("src", "href", "srcset"):
            if name not in attributes:
                continue
            if (tag == "a" and name == "href") or (
                is_canonical and name == "href"
            ):
                continue
            value = attributes[name]
            if value is None:
                self.reporter.error(self.path, line, f"{name} 属性の値が空です")
                continue
            values = srcset_urls(value) if name == "srcset" else [value]
            for target in values:
                check_local_reference(
                    self.path, line, target, self.site_paths, self.reporter
                )

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)


def check_csp(
    path: str,
    parser: SiteHTMLParser,
    reporter: Reporter,
) -> None:
    if not parser.csp_lines:
        reporter.error(
            path,
            1,
            "Content-Security-Policy meta に default-src 'none' を指定してください",
        )
        return
    for line, content in parser.csp_lines:
        value = (content or "").lower()
        if not CSP_DEFAULT_RE.search(value):
            reporter.error(
                path,
                line,
                "Content-Security-Policy に default-src 'none' が必要です",
            )
        if "unsafe-inline" in value or "unsafe-eval" in value:
            reporter.error(
                path,
                line,
                "Content-Security-Policy で unsafe-inline と unsafe-eval は使えません",
            )


def check_html(
    path: str,
    text: str,
    site_paths: set[str],
    reporter: Reporter,
) -> None:
    parser = SiteHTMLParser(path, site_paths, reporter)
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        reporter.error(path, 1, f"HTML を解析できません: {exc}")
        return
    check_csp(path, parser, reporter)
    for metadata in parser.metadata_urls:
        check_metadata_url(metadata, site_paths, reporter)
    if path == "public_html/index.html":
        check_social_metadata(parser, reporter)


def check_social_metadata(parser: SiteHTMLParser, reporter: Reporter) -> None:
    image_metadata = parser.metadata_properties.get("og:image", [])
    if len(image_metadata) != 1 or image_metadata[0][1] != SOCIAL_WEBP_URL:
        reporter.error(
            parser.path,
            image_metadata[0][0] if image_metadata else 1,
            f"og:image は {SOCIAL_WEBP_URL} を参照してください",
        )

    for property_name, expected in (
        ("og:image:type", "image/webp"),
        ("og:image:width", "1280"),
        ("og:image:height", "640"),
    ):
        values = parser.metadata_properties.get(property_name, [])
        if len(values) != 1 or values[0][1] != expected:
            reporter.error(
                parser.path,
                values[0][0] if values else 1,
                f"{property_name} は {expected} を指定してください",
            )


def check_social_webp(
    root: Path,
    site_paths: set[str],
    reporter: Reporter,
) -> None:
    if SOCIAL_WEBP not in site_paths:
        reporter.error(SOCIAL_WEBP, 1, "Social preview の WebP が追跡されていません")
        return
    try:
        data = (root / SOCIAL_WEBP).read_bytes()
    except OSError as exc:
        reporter.error(SOCIAL_WEBP, 1, f"WebP を読み込めません: {exc}")
        return

    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        reporter.error(SOCIAL_WEBP, 1, "RIFF/WEBP ヘッダーが不正です")
        return
    riff_size = struct.unpack_from("<I", data, 4)[0]
    if riff_size != len(data) - 8:
        reporter.error(SOCIAL_WEBP, 1, "RIFF サイズがファイル長と一致しません")
        return
    if len(data) < 20:
        reporter.error(SOCIAL_WEBP, 1, "VP8L チャンクがありません")
        return
    chunk_type = data[12:16]
    if chunk_type != b"VP8L":
        name = chunk_type.decode("ascii", errors="replace")
        reporter.error(
            SOCIAL_WEBP,
            1,
            f"VP8L のみを使ってください（検出: {name}）",
        )
        return

    chunk_size = struct.unpack_from("<I", data, 16)[0]
    expected_length = 20 + chunk_size + (chunk_size & 1)
    if chunk_size < 5 or expected_length != len(data):
        reporter.error(
            SOCIAL_WEBP,
            1,
            "VP8L チャンク長または奇数長パディングが不正です",
        )
        return
    if data[20] != 0x2F:
        reporter.error(SOCIAL_WEBP, 1, "VP8L のシグネチャが不正です")
        return

    dimensions = struct.unpack_from("<I", data, 21)[0]
    width = 1 + (dimensions & 0x3FFF)
    height = 1 + ((dimensions >> 14) & 0x3FFF)
    if (width, height) != (1280, 640):
        reporter.error(
            SOCIAL_WEBP,
            1,
            f"WebP の寸法は 1280x640 が必要です（検出: {width}x{height}）",
        )


def without_css_comments(text: str) -> str:
    def preserve_lines(match: re.Match[str]) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group())

    return CSS_COMMENT_RE.sub(preserve_lines, text)


def check_css(
    path: str,
    text: str,
    site_paths: set[str],
    reporter: Reporter,
) -> None:
    cleaned = without_css_comments(text)
    for match in CSS_URL_RE.finditer(cleaned):
        value = next(group for group in match.groups() if group is not None).strip()
        line = cleaned.count("\n", 0, match.start()) + 1
        check_local_reference(path, line, value, site_paths, reporter)


def check_logo_copies(
    root: Path,
    all_paths: set[str],
    site_paths: set[str],
    reporter: Reporter,
) -> None:
    for name in LOGO_FILES:
        site_path = f"public_html/images/{name}"
        master_path = f"docs/logo/{name}"
        if site_path not in site_paths:
            reporter.error(site_path, 1, "サイトのロゴコピーが追跡されていません")
            continue
        if master_path not in all_paths:
            reporter.error(master_path, 1, "ロゴのマスターファイルが追跡されていません")
            continue
        site_bytes = read_bytes(root, site_path, reporter)
        master_bytes = read_bytes(root, master_path, reporter)
        if site_bytes is not None and master_bytes is not None and site_bytes != master_bytes:
            reporter.error(
                site_path,
                1,
                "docs/logo/ のマスターと内容が一致しません",
            )


def check_site_patterns(
    root: Path,
    all_paths: set[str],
    reporter: Reporter,
) -> None:
    if SITE_PATTERNS not in all_paths:
        reporter.error(SITE_PATTERNS, 1, "site_patterns.py が追跡されていません")
        return
    result = subprocess.run(
        [sys.executable, str(root / SITE_PATTERNS), "--check"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        reporter.error(
            SITE_PATTERNS,
            1,
            "site_patterns.py --check に失敗しました",
        )


def main() -> int:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--expect-pages-cname")
    args = parser.parse_args()
    root = args.root.resolve()
    reporter = Reporter()

    try:
        all_paths = tracked_paths(root)
        site_paths = tracked_paths(root, "public_html")
    except RuntimeError as exc:
        reporter.error("public_html", 1, f"追跡ファイル一覧を取得できません: {exc}")
        reporter.summary()
        return 1

    check_site_allowlist(site_paths, reporter)
    if args.expect_pages_cname is not None:
        check_expected_pages_cname(args.expect_pages_cname, reporter)

    for path in sorted(item for item in site_paths if item.lower().endswith(".html")):
        text = read_text(root, path, reporter)
        if text is not None:
            check_html(path, text, site_paths, reporter)
    if "public_html/site.css" in site_paths:
        text = read_text(root, "public_html/site.css", reporter)
        if text is not None:
            check_css("public_html/site.css", text, site_paths, reporter)

    check_logo_copies(root, all_paths, site_paths, reporter)
    check_social_webp(root, site_paths, reporter)
    check_site_patterns(root, all_paths, reporter)
    reporter.summary()
    return 1 if reporter.errors else 0


if __name__ == "__main__":
    sys.exit(main())
