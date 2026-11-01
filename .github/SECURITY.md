# Security policy

## Supported versions

The latest released version of `envrelay` receives security fixes.

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub's "Report a
vulnerability" (Security advisories) feature on the repository, rather than
opening a public issue. Include a description of the problem, the affected
version, and a minimal reproduction if possible. You can expect an initial
response within a few days.

`envrelay` writes files atomically and, by default, replaces symlinks rather
than following them (`set_key`/`unset_key` accept `follow_symlinks=True` to opt
in); keep that in mind when editing files at untrusted paths.
