#!/usr/bin/env python3
"""Observe a public release asset without persisting signed URL credentials."""

import argparse
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlsplit, urlunsplit, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen


def redact(url):
    parts = urlsplit(url)
    public = {"se", "skt", "ske", "X-Amz-Date", "X-Amz-Expires"}
    query = [(name, value if name in public else "REDACTED")
             for name, value in parse_qsl(parts.query)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


class Redirects(HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.hops = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append({"status": code, "from": redact(req.full_url),
                          "to": redact(newurl), "date": headers.get("Date")})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="v0.0.0")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    api = "https://api.github.com/repos/uist1idrju3i/MSD-Linux/releases/tags/" + args.tag
    request = Request(api, headers={"User-Agent": "MSD-Linux-RAUC-Phase-A"})
    with urlopen(request, timeout=30) as response:
        release = json.load(response)
    if not release["assets"]:
        record = {"tag": args.tag, "api": api, "status": "no-assets",
                  "published_at": release["published_at"],
                  "release_url": release["html_url"], "asset_count": 0}
        args.output.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record, indent=2))
        raise SystemExit(2)
    asset = min(release["assets"], key=lambda value: value["size"])
    redirect = Redirects()
    opener = build_opener(redirect)
    start = time.monotonic()
    request = Request(asset["browser_download_url"],
                      headers={"User-Agent": "MSD-Linux-RAUC-Phase-A", "Range": "bytes=0-3"})
    try:
        response = opener.open(request, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        body = response.read(4)
        record = {"tag": args.tag, "api": api, "asset": asset["name"],
                  "asset_size": asset["size"], "url": asset["browser_download_url"],
                  "hops": redirect.hops, "status": response.status,
                  "final_url": redact(response.url),
                  "headers": {key: response.headers.get(key) for key in (
                      "Date", "Content-Range", "Content-Length", "Accept-Ranges", "Age", "Via")},
                  "bytes_read": len(body), "first_four_hex": body.hex(),
                  "seconds": time.monotonic() - start,
                  "limitation": "read-only urllib observation, not RAUC verification"}
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
