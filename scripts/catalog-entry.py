#!/usr/bin/env python3
"""catalog-entry.py — put one published version of a module into the catalogue.

Called by scripts/install-module.sh publish. It reads the builds from dist/, computes sha256 and size
of each, and writes (or updates) the entry of this module in catalog.json of matrica-modules-dist.

Why a script and not a hand-edited file: a checksum typed by hand is a checksum nobody can trust, and
the entry must describe exactly the bytes that were uploaded a second ago.

Usage:
  catalog-entry.py --catalog <path to catalog.json> --module gallery --version 0.6.6 \
      --dist dist --bin anytext-gallery \
      --platforms linux-amd64,linux-arm64,windows-amd64,darwin-arm64,darwin-amd64 \
      --names '{"ru":"Галерея","en":"Gallery"}' --description '{"ru":"…","en":"…"}' \
      --category media --repository kirill-scherba/anytext-gallery \
      --addr 127.0.0.1:7860 --args '["-addr","127.0.0.1:7860"]' --ui ui --auto-start
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

# Two addresses for one file, the same pair a release has (docs/DOWNLOADS.md): the storage itself, and
# the relay that fetches it from Moscow. Google refuses some networks — the owner's home among them —
# so the installation tries the storage first and falls back to the relay, and the relay is the road
# for everyone whose network cannot reach Google at all (26.11.2026).
STORAGE = "https://storage.googleapis.com/cooksy-ea86d-anytext-releases/modules"
RELAY = "https://relay.anytext.teonet.dev/download/modules"


def asset(module, version, binary, platform, dist):
    name = f"{binary}-{platform}" + (".exe" if platform.startswith("windows-") else "")
    path = os.path.join(dist, name)
    if not os.path.exists(path):
        print(f"нет сборки {name} в {dist}", file=sys.stderr)
        sys.exit(1)
    with open(path, "rb") as f:
        data = f.read()
    return {
        # url is the one that always works; direct is the storage, tried first because it is faster
        # when a network reaches it.
        "url": f"{RELAY}/{module}/{version}/{name}",
        "direct": f"{STORAGE}/{module}/{version}/{name}",
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--module", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--dist", required=True)
    ap.add_argument("--bin", required=True)
    ap.add_argument("--platforms", required=True)
    ap.add_argument("--names", default="{}")
    ap.add_argument("--description", default="{}")
    ap.add_argument("--category", default="")
    ap.add_argument("--repository", default="")
    ap.add_argument("--docs", default="")
    ap.add_argument("--addr", required=True)
    ap.add_argument("--args", default="[]")
    ap.add_argument("--ui", default="ui")
    ap.add_argument("--mcp", default="")
    ap.add_argument("--licence", default="")
    ap.add_argument("--auto-start", action="store_true")
    a = ap.parse_args()

    catalog = {"schema": 1, "updated": "", "modules": []}
    if os.path.exists(a.catalog):
        with open(a.catalog) as f:
            catalog = json.load(f)
    modules = catalog.setdefault("modules", [])
    entry = next((m for m in modules if m.get("id") == a.module), None)
    if entry is None:
        entry = {
            "id": a.module,
            "names": json.loads(a.names),
            "description": json.loads(a.description),
            "category": a.category,
            "repository": a.repository,
            "docs": a.docs,
            "latest": a.version,
            "versions": {},
        }
        modules.append(entry)

    version = {
        "addr": a.addr,
        "args": json.loads(a.args),
        "ui": a.ui,
        "auto_start": bool(a.auto_start),
        "assets": {},
    }
    if a.mcp:
        version["mcp"] = a.mcp
    if a.licence:
        version["licence"] = a.licence
    for platform in a.platforms.split(","):
        platform = platform.strip()
        if platform:
            version["assets"][platform] = asset(a.module, a.version, a.bin, platform, a.dist)

    entry["latest"] = a.version
    entry.setdefault("versions", {})[a.version] = version
    catalog["updated"] = datetime.date.today().isoformat()

    with open(a.catalog, "w") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"   каталог: {a.catalog} — {a.module} {a.version}, платформ {len(version['assets'])}")


if __name__ == "__main__":
    main()
