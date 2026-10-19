#!/bin/sh
set -eu

repo_root="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"

python3 - "$repo_root" <<'PY'
import json
import pathlib
import subprocess
import sys
import tempfile

root = pathlib.Path(sys.argv[1])
script = root / ".github/scripts/check-site-status.py"
dns_expect = root / ".github/site-dns.tsv"
today = "2036-10-19"


def read_expectations():
    rows = []
    for line in dns_expect.read_text(encoding="utf-8").splitlines()[1:]:
        if line:
            name, record_type, value, _reason = line.split("\t")
            rows.append((name, record_type.upper(), value))
    return rows


expectations = read_expectations()


def base_data():
    pages = {
        "cname": "muromi.moe",
        "https_enforced": True,
        "https_certificate": {
            "state": "approved",
            "domains": ["muromi.moe", "www.muromi.moe"],
            "expires_at": "2036-11-02T00:00:00Z",
        },
    }
    dig = {}
    grouped = {}
    for name, record_type, value in expectations:
        grouped.setdefault((name, record_type), []).append(value)
    for (name, record_type), values in grouped.items():
        for resolver in ("1.1.1.1", "8.8.8.8"):
            dig[f"{name} {record_type} {resolver}"] = list(values)
    dig["msd-linux-wildcard-probe.muromi.moe A 1.1.1.1"] = []
    dig["msd-linux-wildcard-probe.muromi.moe AAAA 1.1.1.1"] = []

    rdap = {
        "https://data.iana.org/rdap/dns.json": {
            "services": [[["moe"], ["https://rdap.fixture.example/"]]]
        },
        "https://rdap.fixture.example/domain/muromi.moe": {
            "events": [
                {
                    "eventAction": "expiration",
                    "eventDate": "2036-12-18T00:00:00Z",
                }
            ]
        },
    }
    canonical = "https://muromi.moe/"
    http = {
        canonical: {"status": 200, "location": None, "error": None},
        "http://muromi.moe/": {
            "status": 301,
            "location": canonical,
            "error": None,
        },
        "http://www.muromi.moe/": {
            "status": 301,
            "location": canonical,
            "error": None,
        },
        "https://www.muromi.moe/": {
            "status": 301,
            "location": canonical,
            "error": None,
        },
    }
    return pages, dig, rdap, http


def run_case(name, expected_rc, expected_row=None, mutate=None, corrupt=None):
    with tempfile.TemporaryDirectory() as directory:
        case = pathlib.Path(directory)
        fixtures = case / "fixtures"
        fixtures.mkdir()
        pages, dig, rdap, http = base_data()
        tsv_path = case / "dns.tsv"
        tsv_path.write_text(dns_expect.read_text(encoding="utf-8"), encoding="utf-8")
        if mutate is not None:
            mutate(pages, dig, rdap, http, tsv_path)
        pages_path = case / "pages.json"
        if corrupt == "pages":
            pages_path.write_text("{", encoding="utf-8")
        else:
            pages_path.write_text(json.dumps(pages), encoding="utf-8")
        if corrupt == "tsv":
            tsv_path.write_text("name\ttype\tvalue\nmuromi.moe\tA\t127.0.0.1\n", encoding="utf-8")
        (fixtures / "dig.json").write_text(json.dumps(dig), encoding="utf-8")
        (fixtures / "rdap.json").write_text(json.dumps(rdap), encoding="utf-8")
        (fixtures / "http.json").write_text(json.dumps(http), encoding="utf-8")
        report_path = case / "report.md"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--pages-json",
                str(pages_path),
                "--dns-expect",
                str(tsv_path),
                "--report",
                str(report_path),
                "--today",
                today,
                "--fixtures",
                str(fixtures),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        assert result.returncode == expected_rc, (
            f"{name}: expected rc={expected_rc}, got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        if expected_rc == 2:
            assert not report_path.exists(), f"{name}: usage error unexpectedly wrote a report"
        else:
            report = report_path.read_text(encoding="utf-8")
            if expected_row is not None:
                assert expected_row in report, f"{name}: missing expected report row\n{report}"
        print(f"ok - {name}")


run_case("all checks pass", 0)


def remove_www(pages, _dig, _rdap, _http, _tsv):
    pages["https_certificate"]["domains"] = ["muromi.moe"]


run_case(
    "certificate domains without www fail",
    1,
    "| 証明書ドメイン | NG |",
    remove_www,
)


def disable_https(pages, _dig, _rdap, _http, _tsv):
    pages["https_enforced"] = False


run_case("https_enforced false fails", 1, "| HTTPS 強制 | NG |", disable_https)


def certificate_expiry(days):
    def mutate(pages, _dig, _rdap, _http, _tsv):
        pages["https_certificate"]["expires_at"] = (
            "2036-11-02T00:00:00Z" if days == 14 else "2036-11-01T00:00:00Z"
        )

    return mutate


run_case("certificate expiry exactly 14 days passes", 0, mutate=certificate_expiry(14))
run_case(
    "certificate expiry 13 days fails",
    1,
    "| 証明書の有効期限 | NG |",
    certificate_expiry(13),
)


def domain_expiry(days):
    def mutate(_pages, _dig, rdap, _http, _tsv):
        expiration = "2036-12-18T00:00:00Z" if days == 60 else "2036-12-17T00:00:00Z"
        rdap["https://rdap.fixture.example/domain/muromi.moe"]["events"][0][
            "eventDate"
        ] = expiration

    return mutate


run_case("RDAP expiry exactly 60 days passes", 0, mutate=domain_expiry(60))
run_case(
    "RDAP expiry 59 days fails",
    1,
    "| ドメイン期限（RDAP） | NG |",
    domain_expiry(59),
)


def add_extra_a(_pages, dig, _rdap, _http, _tsv):
    for resolver in ("1.1.1.1", "8.8.8.8"):
        dig[f"muromi.moe A {resolver}"].append("203.0.113.1")


run_case("extra A record fails", 1, "| DNS muromi.moe A (1.1.1.1) | NG |", add_extra_a)


def remove_txt(_pages, dig, _rdap, _http, _tsv):
    name, record_type, value = next(
        row for row in expectations if row[1] == "TXT"
    )
    for resolver in ("1.1.1.1", "8.8.8.8"):
        dig[f"{name} {record_type} {resolver}"].remove(value)


run_case("missing TXT record fails", 1, "| DNS _github-pages-challenge-", remove_txt)


def add_wildcard(_pages, dig, _rdap, _http, _tsv):
    dig["msd-linux-wildcard-probe.muromi.moe A 1.1.1.1"] = ["192.0.2.10"]


run_case(
    "wildcard answer fails",
    1,
    "| ワイルドカード A (msd-linux-wildcard-probe.muromi.moe) | NG |",
    add_wildcard,
)


def www_tls_error(_pages, _dig, _rdap, http, _tsv):
    http["https://www.muromi.moe/"] = {
        "status": None,
        "location": None,
        "error": "certificate verify failed",
    }


run_case(
    "https www TLS error fails",
    1,
    "| HTTP https://www.muromi.moe/ | NG | 接続に失敗しました: certificate verify failed |",
    www_tls_error,
)


def outside_apex(_pages, _dig, _rdap, _http, tsv_path):
    lines = tsv_path.read_text(encoding="utf-8").splitlines()
    fields = lines[1].split("\t")
    fields[0] = "example.net"
    lines[1] = "\t".join(fields)
    tsv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


run_case("TSV name outside apex fails", 1, "| DNS 設定の apex | NG |", outside_apex)
run_case("corrupt Pages JSON is a usage error", 2, corrupt="pages")
run_case("three-column TSV is a usage error", 2, corrupt="tsv")
PY
