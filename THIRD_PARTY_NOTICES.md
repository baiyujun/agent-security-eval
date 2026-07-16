# Third-Party Notices

No third-party source code or datasets were copied into this repository at initialization or by the
current reference-audit branch. The experiment imports an installed upstream package at runtime; it
does not vendor that package.

[`references/manifest.yaml`](references/manifest.yaml) records external projects considered for
design comparison, future dependencies, adapters, or dataset import. A reference entry does not
mean that its code, data, or license has been adopted.

[The reference reuse analysis](docs/reference-reuse-analysis.md) records the source-level evidence,
reuse decisions, and unresolved provenance questions behind that registry.

Before copying or modifying any external code, the project must record:

- repository URL;
- exact commit SHA;
- upstream file paths;
- applicable license;
- local modifications;
- intended use.

WASP is design-reference-only by default because its repository contains non-commercial and mixed
licensing constraints. Its code and benchmark data must not be copied without explicit review and
approval.
