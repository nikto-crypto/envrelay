# Releasing

Releases are cut from `main` and published by the manual-dispatch GitHub
workflow (`.github/workflows/release.yml`).

## Steps

1. Ensure the test suite is green against the oracle:

   ```bash
   ENVRELAY_REQUIRE_ORACLE=1 .venv/bin/python -m pytest -rs -p no:warnings
   ```

2. Update `CHANGELOG.md` (move items from *Unreleased* under the new version).

3. Bump the version. The single source of truth is
   `src/envrelay/_version.py`; `bump2version` keeps it and `.bumpversion.cfg`
   in sync:

   ```bash
   .venv/bin/bump2version patch   # or minor / major
   ```

   We use `bump2version` (not `bump-my-version`), because the latter pulls in
   pydantic-settings, which depends on python-dotenv.

4. Push the commit and tag.

5. Trigger the **Release** workflow from the GitHub Actions tab. It builds the
   sdist and wheel and publishes them.

## Version location

`pyproject.toml` reads the version dynamically from
`envrelay._version.VERSION`. The top-level package intentionally does not expose
`__version__`.
