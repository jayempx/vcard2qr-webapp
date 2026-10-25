"""Pin only the source revision tested by the current workflow."""

import os
import re
import subprocess
from pathlib import Path

sha = os.environ["GITHUB_SHA"]
repo = os.environ["GITHUB_REPOSITORY"]
if not re.fullmatch(r"[a-f0-9]{40}", sha) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
    raise SystemExit("Invalid release metadata.")
subprocess.run(["git", "fetch", "origin", "main"], check=True)
head = subprocess.check_output(["git", "rev-parse", "origin/main"], text=True).strip()
if head != sha:
    raise SystemExit("A newer commit exists; this run will not promote a stale revision.")
path = Path("compose.portainer.yml")
text = path.read_text()
text = re.sub(r"^x-release: .*$", f'x-release: "{sha}"', text, flags=re.M)
text = re.sub(r"^      context: .*$", f"      context: https://github.com/{repo}.git#{sha}", text, flags=re.M)
text = re.sub(r"^        SOURCE_REVISION: .*$", f'        SOURCE_REVISION: "{sha}"', text, flags=re.M)
path.write_text(text)
