# matrica-modules-dist

The catalogue of public AnyText modules: one file, `catalog.json`, read by every installation at

    https://raw.githubusercontent.com/kirill-scherba/matrica-modules-dist/main/catalog.json

A module is a separate process that an installation starts and proxies (see `docs/MODULES.md` in
anytext-gui). The catalogue says where each version's binary is, its sha256 and size, and how to start
it. A private module — the tender department — has no entry here: an installation cannot install what
it cannot see.

Entries are written by `scripts/publish.py` of this repository, never by hand: a hand-typed checksum is
a checksum nobody can trust.

```
./scripts/publish.py                  # every module of modules.json, all five platforms
./scripts/publish.py tasks calendar   # only these
```

`modules.json` says what the public modules are: their repositories, names, descriptions, addresses and
start arguments. The version is not written there - it is the `const version` of the module's own
`main.go`, so a build cannot be published under a version it does not claim.

The same catalogue is what the setups of AnyText ship: `scripts/fetch-modules.sh` of anytext-gui takes
these builds, checks their sha256 and puts them beside the application.
