# Project Foundation

## Project identity

The Python distribution and installed command are `arxiv-int`; the import package is `arxiv_int`.
`src/arxiv_int/metadata.py` provides the typed `ProjectInfo` value through `project_info()`. It
reports the distribution, package, and installed version, with a source-checkout fallback when
distribution metadata is unavailable.

`src/arxiv_int/cli.py` owns argument parsing. The installed `arxiv-int info` command logs the same
identity, providing an import, packaging, and executable-path smoke test without selecting a corpus,
store, or application framework.

Run it through the stable Make entrypoint:

```bash
make run
```

The separate `arxiv-int-plan` entrypoint supports `make plan-status`. Repository quality modules
remain under `src/arxiv_int/quality/`, and shared shell functions use the `arxiv_int_` prefix.

## Metadata and documentation

`pyproject.toml` carries the `arxiv-int` distribution metadata, project URLs, console scripts,
package discovery, type-check path, and coverage source. `README.md`, `AGENTS.md`, the contributor
guide, current-state pages, tests, Make workflows, and `uv.lock` use the same active identity.

## Tests and verification

`tests/test_metadata.py` covers installed-version lookup and the source-checkout fallback.
`tests/test_cli.py` covers parsing and logged identity. Tests under `tests/quality/` exercise the
renamed quality package and verify the personalized repository plan summary.

The locked bootstrap and import doctor pass, and `make run` reports
`arxiv-int 0.1.0 (arxiv_int)`. The required `make ci` gate passes all 32 tests plus formatting,
linting, typing, complexity, shell, documentation-link, and specification-plan checks. `make build`
produces `dist/arxiv_int-0.1.0.tar.gz` and `dist/arxiv_int-0.1.0-py3-none-any.whl`.
