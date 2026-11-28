#!/usr/bin/env python3
"""Check the tag checkout and the production deployment policy."""

import csv
import json
import os
import re
import runpy
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def check_tag():
    env = os.environ
    ref, tag = env["GITHUB_REF"], env["GITHUB_REF_NAME"]
    event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    if (
        env["GITHUB_EVENT_NAME"] != "push"
        or event.get("deleted") is not False
        or ref != f"refs/tags/{tag}"
        or not tag.startswith("v")
    ):
        raise ValueError("expected a non-deletion version tag push")
    if git("cat-file", "-t", ref) == "tag":
        tag_header = git("cat-file", "tag", ref).splitlines()[2]
        if tag_header != f"tag {tag}":
            raise ValueError("annotated tag name differs from the ref")
    commit = git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if commit != git("rev-parse", "HEAD") or commit != git(
        "rev-parse", "--verify", f"{env['GITHUB_SHA']}^{{commit}}"
    ):
        raise ValueError("tag, event and checkout must identify the same commit")
    git("merge-base", "--is-ancestor", commit, "refs/remotes/origin/main")
    return tag


def get_json(endpoint):
    request = Request(
        f"{os.environ['GITHUB_API_URL']}/{endpoint}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def check_production(fetch=get_json):
    endpoint = f"repos/{os.environ['GITHUB_REPOSITORY']}/environments/production"
    data = fetch(endpoint)
    branch_policy = data["deployment_branch_policy"]
    if (
        data["can_admins_bypass"] is not False
        or branch_policy["protected_branches"] is not False
        or branch_policy["custom_branch_policies"] is not True
        or not any(
            rule["type"] == "required_reviewers"
            and isinstance(rule.get("reviewers"), list)
            and rule["reviewers"]
            for rule in data["protection_rules"]
        )
    ):
        raise ValueError("production must require reviewers and disallow administrator bypass")

    policies = fetch(f"{endpoint}/deployment-branch-policies?per_page=100")
    entries = policies["branch_policies"]
    if (
        type(policies["total_count"]) is not int
        or policies["total_count"] != 1
        or not isinstance(entries, list)
        or [(rule["type"], rule["name"]) for rule in entries] != [("tag", "v*")]
    ):
        raise ValueError("production must only allow the v* tag")


def check_version(tag):
    check = runpy.run_path(str(Path(__file__).with_name("check-releases.py")))
    pattern, version_key = check["TAG_RE"], check["version_key"]
    match = pattern.fullmatch(tag)
    if not match or match.group(4) is None:
        raise ValueError("expected vX.Y.Z-rc.N")
    revision = git("rev-parse", "HEAD")
    number = int(git("show", "-s", "--format=%ct", revision))
    version = version_key(match)
    heading = re.compile(rf"^## \[{re.escape(tag[1:])}\](?:\s|$)", re.MULTILINE)
    if not heading.search(Path("CHANGELOG.md").read_text(encoding="utf-8")):
        raise ValueError("CHANGELOG.md has no heading for the tag")
    ledger = "docs/releases/releases.csv"
    for source, contents in (
        ("tag", Path(ledger).read_text(encoding="utf-8")),
        ("origin/main", git("show", f"refs/remotes/origin/main:{ledger}")),
    ):
        reader = csv.DictReader(contents.splitlines(keepends=True))
        if reader.fieldnames != check["HEADER"]:
            raise ValueError("invalid release ledger header")
        for row in reader:
            recorded = pattern.fullmatch(row["tag"])
            if recorded is None:
                raise ValueError("invalid tag in release ledger")
            if revision == row["commit"] or tag == row["tag"]:
                raise ValueError(f"commit or version already appears in {source} release ledger")
            previous = version_key(recorded)
            update = int(row["update_number"])
            if version <= previous or number <= update:
                raise ValueError(f"commit time must increase in {source} release ledger version order")


def main():
    try:
        if sys.argv[1:]:
            raise ValueError("unknown release policy option")
        check_version(check_tag())
        check_production()
    except (KeyError, IndexError, TypeError, ValueError, OSError,
            subprocess.CalledProcessError) as error:
        print(f"::error::Cannot verify release policy: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
