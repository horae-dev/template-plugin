<p align="center"><img src="https://raw.githubusercontent.com/horae-dev/.github/main/brand/horae-logo-500.png" width="96" alt="Horae logo"></p>

# template-plugin

Template repository for writing a [Horae](https://github.com/horae-dev/horae) plugin: a
`plugin.yaml` manifest, an MCP stdio server built on
[`horae-sdk`](https://github.com/horae-dev/horae/tree/main/sdk), recorded-input tests, CI,
`graft.yaml` and `AGENTS.md`. A repository made from it passes CI unchanged.

## What is in it

| Path | What |
|---|---|
| `src/example_plugin/plugin.py` | The plugin: one source, `example.inbox`, that proposes a `task.create` per message. The message subject is untrusted and reaches the title only through `intents.task_create`, which escapes it for Obsidian Tasks. |
| `src/example_plugin/__main__.py` | `python -m example_plugin` serves it over stdio; `--manifest` prints `plugin.yaml`. |
| `plugin.yaml` | The manifest: what the plugin provides and the permissions it needs (here, only the `task.create` intent). |
| `tests/recordings/` | Recorded calls and their expected data and intents, replayed through MCP by `horae_sdk.testing`. |
| `tests/fixtures/` | Synthetic data the fake client answers with (never real messages). |
| `tests/test_manifest.py` | `plugin.yaml` passes the SDK's manifest checks and matches the code. |
| `tests/test_stdio.py` | The plugin starts and answers over stdio, as the core's plugin host runs it. |
| `.github/workflows/ci.yml` | Lockfile, ruff, mypy (strict), pytest with an 85% coverage gate, gitleaks, and the aggregate **CI OK** check. |
| `graft.yaml`, `AGENTS.md` | Review policy and the working rules for agents and humans. |

`horae-sdk` is not on PyPI yet: `pyproject.toml` takes it from the core repository, pinned to
a commit (`[tool.uv.sources]`), and Renovate bumps that pin weekly. Once it is published,
delete that table and the `horae-sdk (git)` manager in `renovate.json`.

## Use this template

1. **Create the repository**: "Use this template" on GitHub (or
   `gh repo create <owner>/<name> --template horae-dev/template-plugin`). CI runs on the first
   push and passes as is.
2. **Install**: `uv sync` (needs [uv](https://docs.astral.sh/uv/)), and optionally
   `uv run pre-commit install`.
3. **Rename** `example` everywhere it names your plugin:
   - the package directory `src/example_plugin/` and its imports, `packages` in
     `pyproject.toml`, `source` in `[tool.coverage.run]`, the module in `COMMAND` and in the
     `--manifest` commands of this README and `AGENTS.md`;
   - `name` in `pyproject.toml`, `NAME` and the refs (`example.inbox`) in `plugin.py`, the
     `tool` of each recording. A plugin name matches `^[a-z][a-z0-9-]*$`; a ref is
     `<namespace>.<tool>`.

   `grep -rn example_plugin --exclude-dir=.venv .` and `grep -rn '"example' tests` find them.
4. **Write the plugin** in `plugin.py`: replace `Inbox` / `SampleInbox` with your service's
   client and the source with your tools. Read the
   [SDK README](https://github.com/horae-dev/horae/blob/main/sdk/README.md) for the roles,
   the intents and what is trusted. Declare the least you need in `PERMISSIONS`: every
   network host, secret, path and intent type.
5. **Regenerate the manifest**: `uv run python -m example_plugin --manifest > plugin.yaml`.
6. **Record fixtures**: put synthetic data in `tests/fixtures/`, one JSON file per call in
   `tests/recordings/` (`tool`, `params`, `input` for a transform, and `expect`), then
   `HORAE_SDK_RECORD=1 uv run pytest` writes the current outputs into `expect`. Review the diff
   before committing: what you commit is what CI checks. Include hostile inputs (Tasks
   signifiers, Markdown, links) for every untrusted field.
7. **Run CI locally**, as CI does:

   ```
   uv lock --check
   uv run ruff check && uv run ruff format --check
   uv run mypy
   uv run pytest --cov
   ```

8. **Install it in Horae**: point the core at `plugin.yaml` with `runtime.command` pinned to
   an absolute interpreter that has your package installed (see "The command" in the SDK
   README).

## Contributing

This project is developed mostly by AI coding agents supervised by a human maintainer. Read
[AGENTS.md](AGENTS.md) for the workflow (it applies to humans too), and the organization's
[contributing guide](https://github.com/horae-dev/.github/blob/main/CONTRIBUTING.md) and
[security policy](https://github.com/horae-dev/.github/blob/main/SECURITY.md).

## License

[Apache-2.0](LICENSE)
