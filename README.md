# matrica-modules-dist

The catalogue of public AnyText modules: one file, `catalog.json`, read by every installation at

    https://raw.githubusercontent.com/kirill-scherba/matrica-modules-dist/main/catalog.json

A module is a separate process that an installation starts and proxies (see `docs/MODULES.md` in
anytext-gui). A private module — the tender department — has no entry here: an installation cannot
install what it cannot see.

## How an entry appears

Nothing in this repository is written by hand:

1. the module's own repository declares it in `module.json` — id, names, description, address, start
   arguments, whether the binary is stripped;
2. its `.github/workflows/release.yml` builds the five platforms on a `v*` tag, checks that the tag is
   the `const version` of `main.go`, runs the tests, and attaches the binaries with their `.sha256` to
   a GitHub release;
3. `build_catalog.py` here reads those declarations and the newest release of each repository and
   writes `catalog.json`. `.github/workflows/catalog.yml` runs it daily, on demand (one button after a
   release) and when `sources.json` or the builder changes.

So a catalogue entry always describes bytes that exist, with the checksum the release carries, and a
release cannot disagree with the catalogue.

```bash
./scripts/…            # does not exist any more: the catalogue is built, not typed
python3 build_catalog.py   # by hand, with GITHUB_TOKEN for a higher API limit
```

`sources.json` names the repositories that publish modules. Adding a module is one line there plus the
declaration in its own repository.

The same catalogue feeds the setups of the application: `scripts/fetch-modules.sh` of anytext-gui takes
these builds, checks their sha256 and puts them beside the application.
