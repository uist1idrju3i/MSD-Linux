#!/usr/bin/env python3
"""Check GitHub Pages, DNS, registration, and HTTP status."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import ssl
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
    urlopen,
)

CERT_MIN_DAYS = 14
DOMAIN_MIN_DAYS = 60
RESOLVERS = ("1.1.1.1", "8.8.8.8")
IANA_RDAP_URL = "https://data.iana.org/rdap/dns.json"
HTTP_TIMEOUT = 15


@dataclass(frozen=True)
class DnsExpectation:
    name: str
    record_type: str
    value: str
    reason: str


@dataclass(frozen=True)
class StatusRow:
    item: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class FetchResult:
    value: Any | None
    error: str | None = None


@dataclass(frozen=True)
class HttpResult:
    status: int | None
    location: str | None
    error: str | None


@dataclass(frozen=True)
class Fixtures:
    dig: dict[str, list[str]]
    rdap: dict[str, dict[str, Any]]
    http: dict[str, dict[str, Any]]


def normalize_name(value: str) -> str:
    return value.strip().rstrip(".").casefold()


def normalize_answer(record_type: str, value: str) -> str:
    answer = value.strip()
    if record_type in {"A", "AAAA"}:
        try:
            return str(ipaddress.ip_address(answer))
        except ValueError:
            return answer.casefold()
    if record_type in {"CNAME", "NS", "PTR", "MX"}:
        return answer.casefold()
    return answer


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: JSON を読み込めません: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: JSON の最上位はオブジェクトである必要があります")
    return value


def parse_dns_expectations(path: Path) -> list[DnsExpectation]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"{path}: TSV を読み込めません: {exc}") from exc
    if not lines or lines[0].split("\t") != ["name", "type", "value", "reason"]:
        raise ValueError(f"{path}: 先頭行は name, type, value, reason の4列である必要があります")

    expectations: list[DnsExpectation] = []
    for number, line in enumerate(lines[1:], 2):
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) != 4:
            raise ValueError(f"{path}:{number}: 4列の TSV が必要です")
        name, record_type, value, reason = (field.strip() for field in fields)
        if not name or not record_type or not value or not reason:
            raise ValueError(f"{path}:{number}: 各列を空にできません")
        expectations.append(
            DnsExpectation(
                normalize_name(name),
                record_type.upper(),
                value,
                reason,
            )
        )
    if not expectations:
        raise ValueError(f"{path}: DNS レコードがありません")
    return expectations


def load_fixtures(directory: Path) -> Fixtures:
    dig = load_json_object(directory / "dig.json")
    rdap = load_json_object(directory / "rdap.json")
    http = load_json_object(directory / "http.json")

    if any(
        not isinstance(key, str)
        or not isinstance(value, list)
        or any(not isinstance(answer, str) for answer in value)
        for key, value in dig.items()
    ):
        raise ValueError(f"{directory / 'dig.json'}: 値は文字列の配列である必要があります")
    if any(
        not isinstance(key, str) or not isinstance(value, dict)
        for key, value in rdap.items()
    ):
        raise ValueError(f"{directory / 'rdap.json'}: 値は JSON オブジェクトである必要があります")
    for key, value in http.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            raise ValueError(f"{directory / 'http.json'}: 値は JSON オブジェクトである必要があります")
        status = value.get("status")
        location = value.get("location")
        error = value.get("error")
        if (
            (status is not None and (not isinstance(status, int) or isinstance(status, bool)))
            or (location is not None and not isinstance(location, str))
            or (error is not None and not isinstance(error, str))
        ):
            raise ValueError(f"{directory / 'http.json'}: status/location/error の値が不正です")

    return Fixtures(dig, rdap, http)


class Fetchers:
    def __init__(self, fixtures: Fixtures | None) -> None:
        self.fixtures = fixtures
        self.http_opener = build_opener(
            NoRedirectHandler(),
            HTTPSHandler(context=ssl.create_default_context()),
        )

    def dns(
        self, name: str, record_type: str, resolver: str, wildcard: bool = False
    ) -> FetchResult:
        key = f"{name} {record_type} {resolver}"
        if self.fixtures is not None:
            answers = self.fixtures.dig.get(key)
            if answers is None:
                return FetchResult(None, f"fixture に DNS query がありません: {key}")
            return FetchResult(answers)

        command = ["dig", "+short"]
        if not wildcard:
            command.extend(("+time=5", "+tries=2"))
        command.extend((f"@{resolver}", name, record_type))
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=HTTP_TIMEOUT,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return FetchResult(None, str(exc))
        if result.returncode:
            output = result.stderr.strip() or result.stdout.strip()
            return FetchResult(
                None,
                f"dig が終了コード {result.returncode} を返しました"
                + (f": {output}" if output else ""),
            )
        return FetchResult([line.strip() for line in result.stdout.splitlines() if line.strip()])

    def rdap(self, url: str) -> FetchResult:
        if self.fixtures is not None:
            value = self.fixtures.rdap.get(url)
            if value is None:
                return FetchResult(None, f"fixture に RDAP response がありません: {url}")
            return FetchResult(value)

        request = Request(url, headers={"Accept": "application/rdap+json, application/json"})
        try:
            with urlopen(request, timeout=HTTP_TIMEOUT) as response:
                value = json.loads(response.read().decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, URLError) as exc:
            return FetchResult(None, str(exc))
        if not isinstance(value, dict):
            return FetchResult(None, "RDAP response の最上位が JSON object ではありません")
        return FetchResult(value)

    def http(self, url: str) -> HttpResult:
        if self.fixtures is not None:
            value = self.fixtures.http.get(url)
            if value is None:
                return HttpResult(None, None, f"fixture に HTTP response がありません: {url}")
            return HttpResult(value.get("status"), value.get("location"), value.get("error"))

        request = Request(url, method="GET")
        try:
            with self.http_opener.open(request, timeout=HTTP_TIMEOUT) as response:
                return HttpResult(response.status, response.headers.get("Location"), None)
        except HTTPError as exc:
            return HttpResult(exc.code, exc.headers.get("Location"), None)
        except (OSError, URLError, TimeoutError) as exc:
            return HttpResult(None, None, str(exc))


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Request,
        response: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


def parse_expiration(value: Any) -> date:
    if not isinstance(value, str) or not value:
        raise ValueError("期限日時がありません")
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError as exc:
        raise ValueError(f"期限日時を解析できません: {value}") from exc


def check_pages_api(pages: dict[str, Any], today: date) -> tuple[list[StatusRow], str]:
    rows: list[StatusRow] = []
    raw_cname = pages.get("cname")
    apex = normalize_name(raw_cname) if isinstance(raw_cname, str) else ""
    rows.append(
        StatusRow(
            "Pages API cname",
            bool(apex),
            f"apex={apex}" if apex else "Pages API の cname がありません",
        )
    )

    https_enforced = pages.get("https_enforced") is True
    rows.append(
        StatusRow(
            "HTTPS 強制",
            https_enforced,
            "https_enforced=true" if https_enforced else "https_enforced が true ではありません",
        )
    )

    certificate = pages.get("https_certificate")
    if not isinstance(certificate, dict):
        certificate = {}
    state = certificate.get("state")
    rows.append(
        StatusRow(
            "証明書の状態",
            state == "approved",
            f"state={state}" if state is not None else "https_certificate.state がありません",
        )
    )

    domains = certificate.get("domains")
    actual_domains = (
        {normalize_name(domain) for domain in domains if isinstance(domain, str)}
        if isinstance(domains, list)
        else set()
    )
    required_domains = {apex, f"www.{apex}"} if apex else set()
    missing_domains = sorted(required_domains - actual_domains)
    rows.append(
        StatusRow(
            "証明書ドメイン",
            bool(apex) and not missing_domains,
            (
                "必要なドメインを含みます: " + ", ".join(sorted(required_domains))
                if apex and not missing_domains
                else "証明書にありません: " + ", ".join(missing_domains or ["apex を判定できません"])
            ),
        )
    )

    try:
        expires_on = parse_expiration(certificate.get("expires_at"))
        days_left = (expires_on - today).days
        rows.append(
            StatusRow(
                "証明書の有効期限",
                days_left >= CERT_MIN_DAYS,
                f"{expires_on.isoformat()} まであと {days_left} 日（基準 {CERT_MIN_DAYS} 日）",
            )
        )
    except ValueError as exc:
        rows.append(StatusRow("証明書の有効期限", False, str(exc)))
    return rows, apex


def check_tsv_apex(expectations: list[DnsExpectation], apex: str) -> StatusRow:
    outside = sorted(
        {
            record.name
            for record in expectations
            if not apex
            or (record.name != apex and not record.name.endswith(f".{apex}"))
        }
    )
    return StatusRow(
        "DNS 設定の apex",
        bool(apex) and not outside,
        (
            f"すべて {apex} またはそのサブドメインです"
            if apex and not outside
            else "apex の外にあります: " + ", ".join(outside or ["Pages API の cname を判定できません"])
        ),
    )


def expected_dns_sets(
    expectations: list[DnsExpectation],
) -> dict[tuple[str, str], set[str]]:
    result: dict[tuple[str, str], set[str]] = {}
    for record in expectations:
        key = (normalize_name(record.name), record.record_type)
        result.setdefault(key, set()).add(
            normalize_answer(record.record_type, record.value)
        )
    return result


def check_dns_records(
    expected: dict[tuple[str, str], set[str]],
    answers: dict[tuple[str, str, str], FetchResult],
) -> list[StatusRow]:
    rows: list[StatusRow] = []
    for (name, record_type), expected_values in sorted(expected.items()):
        for resolver in RESOLVERS:
            item = f"DNS {name} {record_type} ({resolver})"
            result = answers.get((name, record_type, resolver))
            if result is None or result.error:
                error = result.error if result is not None else "DNS query の結果がありません"
                rows.append(StatusRow(item, False, f"dig に失敗しました: {error}"))
                continue
            actual_values = {
                normalize_answer(record_type, value)
                for value in result.value
                if isinstance(value, str)
            }
            missing = sorted(expected_values - actual_values)
            extra = sorted(actual_values - expected_values)
            if missing or extra:
                details = []
                if missing:
                    details.append("不足: " + ", ".join(missing))
                if extra:
                    details.append("余分: " + ", ".join(extra))
                rows.append(StatusRow(item, False, "。".join(details)))
            else:
                rows.append(
                    StatusRow(
                        item,
                        True,
                        "回答セットが一致しました: " + ", ".join(sorted(actual_values)),
                    )
                )
    return rows


def check_wildcard(name: str, record_type: str, result: FetchResult) -> StatusRow:
    item = f"ワイルドカード {record_type} ({name})"
    if result.error or result.value is None:
        return StatusRow(
            item,
            False,
            f"dig に失敗しました: {result.error or 'DNS query の結果がありません'}",
        )
    answers = [value.strip() for value in result.value if isinstance(value, str) and value.strip()]
    return StatusRow(
        item,
        not answers,
        "回答はありません" if not answers else "予期しない回答: " + ", ".join(sorted(answers)),
    )


def rdap_domain_url(registry: dict[str, Any], apex: str) -> str:
    tld = apex.rsplit(".", 1)[-1].casefold()
    services = registry.get("services")
    if not isinstance(services, list):
        raise ValueError("IANA RDAP registry に services がありません")
    for service in services:
        if not isinstance(service, list) or len(service) < 2:
            continue
        tlds, bases = service[0], service[1]
        if not isinstance(tlds, list) or not isinstance(bases, list):
            continue
        if not any(isinstance(value, str) and value.strip(".").casefold() == tld for value in tlds):
            continue
        base = next((value for value in bases if isinstance(value, str) and value), None)
        if base is not None:
            return f"{base.rstrip('/')}/domain/{quote(apex, safe='')}"
    raise ValueError(f"IANA RDAP registry に .{tld} の base URL がありません")


def check_domain_expiration(
    apex: str,
    registry: FetchResult,
    domain: FetchResult,
    today: date,
) -> StatusRow:
    item = "ドメイン期限（RDAP）"
    if not apex:
        return StatusRow(item, False, "Pages API の cname から apex を取得できません")
    if registry.error or not isinstance(registry.value, dict):
        return StatusRow(
            item,
            False,
            f"IANA RDAP registry を取得できません: {registry.error or 'JSON object がありません'}",
        )
    try:
        rdap_domain_url(registry.value, apex)
    except ValueError as exc:
        return StatusRow(item, False, str(exc))
    if domain.error or not isinstance(domain.value, dict):
        return StatusRow(
            item,
            False,
            f"RDAP domain response を取得できません: {domain.error or 'JSON object がありません'}",
        )

    events = domain.value.get("events")
    expiration = None
    if isinstance(events, list):
        expiration = next(
            (
                event.get("eventDate")
                for event in events
                if isinstance(event, dict)
                and isinstance(event.get("eventAction"), str)
                and event["eventAction"].casefold() == "expiration"
            ),
            None,
        )
    try:
        expires_on = parse_expiration(expiration)
    except ValueError as exc:
        return StatusRow(item, False, f"RDAP expiration: {exc}")
    days_left = (expires_on - today).days
    return StatusRow(
        item,
        days_left >= DOMAIN_MIN_DAYS,
        f"{expires_on.isoformat()} まであと {days_left} 日（基準 {DOMAIN_MIN_DAYS} 日）",
    )


def http_targets(apex: str) -> list[tuple[str, int, str | None]]:
    if not apex:
        return []
    canonical = f"https://{apex}/"
    return [
        (canonical, 200, None),
        (f"http://{apex}/", 301, canonical),
        (f"http://www.{apex}/", 301, canonical),
        (f"https://www.{apex}/", 301, canonical),
    ]


def check_http_responses(
    apex: str, responses: dict[str, HttpResult]
) -> list[StatusRow]:
    if not apex:
        return [
            StatusRow(
                "HTTP/HTTPS URL",
                False,
                "Pages API の cname から URL を作成できません",
            )
            for _ in range(4)
        ]
    rows: list[StatusRow] = []
    for url, expected_status, expected_location in http_targets(apex):
        item = f"HTTP {url}"
        result = responses.get(url)
        if result is None:
            rows.append(StatusRow(item, False, "HTTP response がありません"))
        elif result.error:
            rows.append(StatusRow(item, False, f"接続に失敗しました: {result.error}"))
        elif result.status != expected_status:
            rows.append(
                StatusRow(
                    item,
                    False,
                    f"status={result.status}（期待: {expected_status}）"
                    + (f", Location={result.location}" if result.location else ""),
                )
            )
        elif expected_location is not None and result.location != expected_location:
            rows.append(
                StatusRow(
                    item,
                    False,
                    f"Location={result.location!r}（期待: {expected_location}）",
                )
            )
        else:
            detail = f"status={result.status}"
            if expected_location is not None:
                detail += f", Location={result.location}"
            rows.append(StatusRow(item, True, detail))
    return rows


def build_report(
    pages: dict[str, Any],
    expectations: list[DnsExpectation],
    fetchers: Fetchers,
    today: date,
) -> list[StatusRow]:
    rows, apex = check_pages_api(pages, today)
    rows.append(check_tsv_apex(expectations, apex))

    expected = expected_dns_sets(expectations)
    dns_answers: dict[tuple[str, str, str], FetchResult] = {}
    for name, record_type in sorted(expected):
        for resolver in RESOLVERS:
            dns_answers[(name, record_type, resolver)] = fetchers.dns(
                name, record_type, resolver
            )
    rows.extend(check_dns_records(expected, dns_answers))

    if apex:
        for record_type in ("A", "AAAA"):
            wildcard_name = f"msd-linux-wildcard-probe.{apex}"
            rows.append(
                check_wildcard(
                    wildcard_name,
                    record_type,
                    fetchers.dns(wildcard_name, record_type, "1.1.1.1", wildcard=True),
                )
            )
    else:
        rows.extend(
            check_wildcard("", record_type, FetchResult(None, "apex がありません"))
            for record_type in ("A", "AAAA")
        )

    registry = fetchers.rdap(IANA_RDAP_URL) if apex else FetchResult(None, "apex がありません")
    domain = FetchResult(None, "RDAP domain URL を取得できません")
    if apex and isinstance(registry.value, dict):
        try:
            domain = fetchers.rdap(rdap_domain_url(registry.value, apex))
        except ValueError as exc:
            domain = FetchResult(None, str(exc))
    rows.append(check_domain_expiration(apex, registry, domain, today))

    responses = {
        url: fetchers.http(url)
        for url, _, _ in http_targets(apex)
    }
    rows.extend(check_http_responses(apex, responses))
    return rows


def render_report(rows: list[StatusRow], today: date) -> str:
    failures = sum(not row.ok for row in rows)
    state = "OK" if failures == 0 else "NG"
    lines = [
        f"公開サイトの状態確認: {today.isoformat()} / {state} "
        f"（{len(rows) - failures}/{len(rows)} 項目 OK）",
        "",
        "| 項目 | 結果 (OK/NG) | 詳細 |",
        "|---|---|---|",
    ]
    for row in rows:
        result = "OK" if row.ok else "NG"
        detail = row.detail.replace("|", "\\|").replace("\r", " ").replace("\n", " ")
        lines.append(f"| {row.item} | {result} | {detail} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages-json", required=True, type=Path)
    parser.add_argument("--dns-expect", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--today")
    parser.add_argument("--fixtures", type=Path)
    args = parser.parse_args()

    try:
        if args.today is not None:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.today) is None:
                raise ValueError("--today は YYYY-MM-DD 形式で指定してください")
            today = date.fromisoformat(args.today)
        else:
            today = date.today()
        pages = load_json_object(args.pages_json)
        expectations = parse_dns_expectations(args.dns_expect)
        fixtures = load_fixtures(args.fixtures) if args.fixtures is not None else None
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rows = build_report(pages, expectations, Fetchers(fixtures), today)
    report = render_report(rows, today)
    try:
        args.report.write_text(report, encoding="utf-8")
    except OSError as exc:
        print(f"error: レポートを書き込めません: {exc}", file=sys.stderr)
        return 2
    print(report.splitlines()[0])
    return 1 if any(not row.ok for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
