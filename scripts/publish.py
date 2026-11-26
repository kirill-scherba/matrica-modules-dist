#!/usr/bin/env python3
"""publish.py — build the public modules for every platform, upload the builds, write the catalogue.

    ./scripts/publish.py                 every module of modules.json
    ./scripts/publish.py tasks calendar  only these
    ./scripts/publish.py --skip-build tasks    upload what is in dist/ already
    ./scripts/publish.py --no-push tasks       write catalog.json, do not commit

A module is a static Go binary, so one machine builds all the platforms the application itself builds:
linux-amd64, linux-arm64, windows-amd64, darwin-arm64, darwin-amd64 (docs/DOWNLOADS.md in anytext-gui).

The version is not an argument: it is the `const version` of the module's own main.go. A build made
after a change but without a version bump would otherwise replace published bytes under a name that
already exists, and an installation would keep the old file because its checksum is in its registry.

The catalogue entry is written by scripts/catalog-entry.py — the same file the gallery's own
install-module.sh uses, so url/direct/sha256/size are computed one way and one way only.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CATALOG = os.path.join(ROOT, "catalog.json")
MODULES = os.path.join(ROOT, "modules.json")
BUCKET = "gs://cooksy-ea86d-anytext-releases/modules"
PLATFORMS = ["linux-amd64", "linux-arm64", "windows-amd64", "darwin-arm64", "darwin-amd64"]
GSUTIL = os.environ.get("GSUTIL") or os.path.expanduser("~/google-cloud-sdk/bin/gsutil")


def log(msg):
    print(f"\033[1m== {msg}\033[0m", flush=True)


def version_of(repo):
    """The module's own version: main.go declares it, and nothing else may decide it."""
    with open(os.path.join(repo, "main.go")) as f:
        m = re.search(r'const\s+version\s*=\s*"([^"]+)"', f.read())
    if not m:
        sys.exit(f"нет const version в {repo}/main.go")
    return m.group(1)


def asset_name(binary, platform):
    return f"{binary}-{platform}" + (".exe" if platform.startswith("windows-") else "")


def build(module, platforms):
    repo = os.path.expanduser(module["repo"])
    dist = os.path.join(repo, "dist")
    os.makedirs(dist, exist_ok=True)
    for platform in platforms:
        goos, goarch = platform.split("-")
        name = asset_name(module["bin"], platform)
        env = dict(os.environ, CGO_ENABLED="0", GOOS=goos, GOARCH=goarch)
        subprocess.run(
            ["go", "build", "-trimpath", "-ldflags", "-s -w", "-o", os.path.join(dist, name), "."],
            cwd=repo, env=env, check=True,
        )
        size = os.path.getsize(os.path.join(dist, name))
        print(f"   {name:<44} {size:>10} байт", flush=True)
    return dist


def upload(module, version, dist, platforms):
    bucket = f"{BUCKET}/{module['id']}/{version}"
    for platform in platforms:
        name = asset_name(module["bin"], platform)
        path = os.path.join(dist, name)
        subprocess.run([GSUTIL, "-q", "-h", "Cache-Control:no-store", "cp", path, f"{bucket}/{name}"], check=True)
        subprocess.run(
            [GSUTIL, "-q", "setmeta", "-h", "Content-Type:application/octet-stream",
             "-h", f'Content-Disposition:attachment; filename="{name}"', f"{bucket}/{name}"],
            check=True,
        )
    print(f"   {bucket}: {len(platforms)} файлов", flush=True)


def catalog_entry(module, version, dist, platforms):
    spec = importlib.util.spec_from_file_location("catalog_entry", os.path.join(HERE, "catalog-entry.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    entry = json.load(open(CATALOG)) if os.path.exists(CATALOG) else {"schema": 1, "updated": "", "modules": []}
    modules = entry.setdefault("modules", [])
    item = next((m for m in modules if m.get("id") == module["id"]), None)
    if item is None:
        item = {
            "id": module["id"],
            "names": module["names"],
            "description": module["description"],
            "category": module.get("category", ""),
            "repository": module.get("repository", ""),
            "docs": module.get("docs", ""),
            "latest": version,
            "versions": {},
        }
        modules.append(item)
    ver = {
        "addr": module["addr"],
        "args": module.get("args", []),
        "ui": module.get("ui", "ui"),
        "auto_start": bool(module.get("auto_start")),
        "assets": {p: mod.asset(module["id"], version, module["bin"], p, dist) for p in platforms},
    }
    if module.get("mcp"):
        ver["mcp"] = module["mcp"]
    item["latest"] = version
    item.setdefault("versions", {})[version] = ver
    import datetime
    entry["updated"] = datetime.date.today().isoformat()
    with open(CATALOG, "w") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"   каталог: {module['id']} {version}, платформ {len(ver['assets'])}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="module ids (default: every module of modules.json)")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()

    modules = json.load(open(MODULES))["modules"]
    if a.ids:
        wanted = set(a.ids)
        unknown = wanted - {m["id"] for m in modules}
        if unknown:
            sys.exit(f"нет таких модулей: {', '.join(sorted(unknown))}")
        modules = [m for m in modules if m["id"] in wanted]

    for module in modules:
        repo = os.path.expanduser(module["repo"])
        if not os.path.isdir(os.path.join(repo, ".git")):
            print(f"   {module['id']}: нет репозитория {repo}", file=sys.stderr)
            continue
        dirty = subprocess.run(["git", "-C", repo, "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        if dirty:
            print(f"   {module['id']}: в рабочем дереве есть незакоммиченное — публикую как есть:\n{dirty}", file=sys.stderr)
        version = version_of(repo)
        log(f"{module['id']} {version}")
        dist = build(module, PLATFORMS) if not a.skip_build else os.path.join(repo, "dist")
        upload(module, version, dist, PLATFORMS)
        catalog_entry(module, version, dist, PLATFORMS)

    if a.no_push:
        log("catalog.json записан, не закоммичен (--no-push)")
        return
    subprocess.run(["git", "-C", ROOT, "add", "catalog.json", "modules.json", "scripts"], check=True)
    ids = ", ".join(f"{m['id']} {version_of(os.path.expanduser(m['repo']))}" for m in modules)
    subprocess.run(["git", "-C", ROOT, "commit", "-q", "-m", f"catalog: {ids}"], check=True)
    subprocess.run(["git", "-C", ROOT, "push", "-q", "origin", "main"], check=True)
    log(f"каталог запушен: {ids}")


if __name__ == "__main__":
    main()
