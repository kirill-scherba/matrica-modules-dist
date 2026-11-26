#!/usr/bin/env python3
"""Build catalog.json from the repositories that publish modules.

Each repository declares its module in `module.json` at its root: the id, the names, the address it
listens on, the arguments it starts with. The version is not declared anywhere by hand: it is the tag of
the newest release, `v<version>`, and the assets are the files that release carries, each with its own
`.sha256`.

Nothing is typed by hand, so the catalogue cannot drift from what is actually published: a module that
was never released has no entry, and an entry always describes bytes that exist.

Run by `.github/workflows/catalog.yml` on a schedule, on demand, and when this script or `sources.json`
changes. The same script runs by hand: `python3 build_catalog.py`.

    GITHUB_TOKEN=... python3 build_catalog.py     # a token raises the API limit; it is optional
"""
import datetime
import json
import os
import sys
import urllib.request

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
BRANCH = "main"
PLATFORMS = ("linux-amd64", "linux-arm64", "windows-amd64", "darwin-arm64", "darwin-amd64")


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "matrica-modules-catalog"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=40) as resp:
        body = resp.read()
    return body.decode() if raw else json.loads(body)


def module_manifest(repo, branch):
    """module.json of a repository; main and master are both tried, because both are in use."""
    for name in (branch, "master"):
        try:
            return json.loads(get(f"{RAW}/{repo}/{name}/module.json", raw=True))
        except Exception as exc:  # noqa: BLE001
            last = exc
    print(f"  {repo}: no module.json ({last})", file=sys.stderr)
    return None


def newest_release(repo):
    """The newest release, not a draft and not a prerelease: a tag alone publishes nothing until it has
    a release with the files on it."""
    for rel in get(f"{API}/repos/{repo}/releases?per_page=30"):
        if rel.get("draft") or rel.get("prerelease"):
            continue
        if rel.get("tag_name", "").startswith("v"):
            return rel
    return None


def sha_of(assets, name):
    """The checksum the workflow wrote next to the binary: `sha256sum` output, hash first."""
    if name + ".sha256" not in assets:
        return ""
    text = get(assets[name + ".sha256"]["browser_download_url"], raw=True).split()
    return text[0] if text else ""


def collect_assets(release, manifest, version):
    assets = {a["name"]: a for a in release.get("assets", [])}
    out = {}
    for platform in manifest.get("platforms") or PLATFORMS:
        name = f"{manifest['binary']}-{platform}" + (".exe" if platform.startswith("windows-") else "")
        if name not in assets:
            print(f"  {manifest['id']}: no build for {platform}", file=sys.stderr)
            continue
        sha = sha_of(assets, name)
        if not sha:
            print(f"  {manifest['id']}: no sha256 for {name}, left out", file=sys.stderr)
            continue
        out[platform] = {"url": assets[name]["browser_download_url"], "sha256": sha, "size": assets[name]["size"]}
    return out


def build():
    sources = json.load(open("sources.json"))
    modules = []

    for src in sources["repos"]:
        repo = src["repo"]
        print(repo)
        manifest = module_manifest(repo, src.get("branch", BRANCH))
        if not manifest:
            continue
        release = newest_release(repo)
        if not release:
            print(f"  {repo}: no release", file=sys.stderr)
            continue
        version = release["tag_name"].lstrip("v")
        assets = collect_assets(release, manifest, version)
        if not assets:
            continue
        modules.append({
            "id": manifest["id"],
            "names": manifest.get("names") or {},
            "description": manifest.get("description") or {},
            "category": manifest.get("category", "tools"),
            "repository": f"https://github.com/{repo}",
            "docs": manifest.get("docs", ""),
            "latest": version,
            "versions": {
                version: {
                    "addr": manifest["addr"],
                    "args": manifest.get("args") or [],
                    "ui": manifest.get("ui", "ui"),
                    "auto_start": bool(manifest.get("auto_start")),
                    "assets": assets,
                }
            },
        })

    modules.sort(key=lambda m: m["id"])
    catalog = {"schema": 1, "updated": datetime.date.today().isoformat(), "modules": modules}
    with open("catalog.json", "w") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"== catalog.json: {len(modules)} модулей")
    for m in modules:
        print(f"   {m['id']:<10} {m['latest']:<8} платформ {len(m['versions'][m['latest']]['assets'])}")


if __name__ == "__main__":
    build()
