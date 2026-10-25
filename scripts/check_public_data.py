"""Audit tracked source/history without echoing rejected private values."""

import argparse
import json
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--history", action="store_true")
parser.add_argument("--denylist")
args = parser.parse_args()
deny = json.loads(Path(args.denylist).read_text()) if args.denylist else []
failures = []


def check(data, location):
    text = data.decode("utf-8", errors="replace")
    lower = text.lower()
    if any(value.lower() in lower for value in deny if value):
        failures.append((location, "private-denylist"))
    if re.search(r"(?i)[a-z]:[\\/](?:users|tmp_loc)[\\/]", text):
        failures.append((location, "workstation-path"))
    if re.search(r"\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)\b", text):
        failures.append((location, "private-address"))
    for email in re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        domain = email.split("@")[-1]
        if not (
            domain.endswith(".example")
            or domain
            in ("example.com", "example.org", "example.net", "qr.invalid", "users.noreply.github.com")
        ):
            failures.append((location, "non-example-email"))


files = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
for name in filter(None, files):
    check(name.encode(), "filename")
    check(Path(name).read_bytes(), name)
if args.history:
    objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], text=True).splitlines()
    for line in objects:
        oid = line.split(" ", 1)[0]
        if " " in line:
            check(line.split(" ", 1)[1].encode(), "historical-path")
        kind = subprocess.check_output(["git", "cat-file", "-t", oid], text=True).strip()
        if kind == "blob":
            check(subprocess.check_output(["git", "cat-file", "blob", oid]), "historical-blob")
        elif kind in ("commit", "tag"):
            check(subprocess.check_output(["git", "cat-file", kind, oid]), "historical-metadata")
    identities = subprocess.check_output(["git", "log", "--all", "--format=%ae%n%ce"], text=True).splitlines()
    if any(not email.endswith("@users.noreply.github.com") for email in identities):
        failures.append(("commit metadata", "non-noreply-identity"))
    names = subprocess.check_output(
        ["git", "log", "--all", "--format=%an%x09%ae%n%cn%x09%ce"], text=True
    ).splitlines()
    for pair in names:
        name, email = pair.split("\t", 1)
        account = email.split("@")[0].split("+", 1)[-1]
        if name != account:
            failures.append(("commit metadata", "non-account-author-name"))
if failures:
    for location, category in sorted(set(failures)):
        print(f"REJECTED {category}: {location}")
    raise SystemExit(1)
print("Public data checks passed.")
