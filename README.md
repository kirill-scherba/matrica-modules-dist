# matrica-modules-dist

The catalogue of public AnyText modules: one file, `catalog.json`, read by every installation at

    https://raw.githubusercontent.com/kirill-scherba/matrica-modules-dist/main/catalog.json

A module is a separate process that an installation starts and proxies (see `docs/MODULES.md` in
anytext-gui). The catalogue says where each version's binary is, its sha256 and size, and how to start
it. A private module — the tender department — has no entry here: an installation cannot install what
it cannot see.

Entries are written by `scripts/install-module.sh publish` of the module's own repository, never by
hand: a hand-typed checksum is a checksum nobody can trust.
