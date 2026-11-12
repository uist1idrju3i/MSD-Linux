#!/usr/bin/env python3
"""Maintain a monitoring issue; callers serialize writers with workflow concurrency."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def gh(*args: str, body: str | None = None) -> str:
    return subprocess.run(["gh", *args], input=body, text=True,
                          stdout=subprocess.PIPE, check=True).stdout.strip()


def find_issue(repository: str, title: str) -> str:
    page = 1
    while True:
        issues = json.loads(gh("api", "--method", "GET",
                              f"repos/{repository}/issues?state=open&per_page=100&page={page}"))
        if not isinstance(issues, list):
            raise ValueError("issue listing must be an array")
        for issue in issues:
            if (not isinstance(issue, dict) or not isinstance(issue.get("number"), int)
                    or not isinstance(issue.get("title"), str)):
                raise ValueError("invalid issue listing")
            if "pull_request" not in issue and issue.get("title") == title:
                return str(issue["number"])
        if len(issues) < 100:
            return ""
        page += 1


def maintain(repository: str, title: str, body: str, clear: bool = False) -> str:
    number = find_issue(repository, title)
    if clear:
        if number:
            gh("issue", "comment", number, "--repo", repository, "--body-file", "-", body=body)
            gh("issue", "close", number, "--repo", repository)
        return number
    if not number:
        number = find_issue(repository, title)
    if number:
        gh("issue", "edit", number, "--repo", repository, "--body-file", "-", body=body)
        return number
    url = gh("issue", "create", "--repo", repository, "--title", title,
             "--body-file", "-", body=body)
    return str(int(url.rsplit("/", 1)[-1]))


def summary(body: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with Path(path).open("a", encoding="utf-8") as stream:
            stream.write(body + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--status", choices=("findings", "clear", "failed"), required=True)
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    failed = args.status == "failed"
    try:
        if failed:
            body = f"# {args.title}\n\n監視に失敗しました。結果は未確認です。件数や解消を判定できません。"
        else:
            if args.body_file is None:
                raise ValueError("a successful report requires a body")
            body = args.body_file.read_text(encoding="utf-8")
            if not body.strip():
                raise ValueError("empty monitoring report")
        body += f"\n\n実行: {args.run_url}\n"
        if failed:
            summary(body)
        number = maintain(os.environ["GITHUB_REPOSITORY"], args.title, body,
                          clear=args.status == "clear")
        if not failed:
            summary(body)
        if number:
            print(number)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
        summary("監視結果の反映に失敗しました。結果は未確認です。\n")
        print("tracking-issue: monitoring report failed", file=sys.stderr)
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
