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
| `tests/test_network.py` | How the approved hosts reach a plugin (`Call.host_allowed`, `address_allowed`) and how to test them with `horae_sdk.testing.call(..., network=..., network_local=...)`. |
| `tests/test_stdio.py` | The plugin starts and answers over stdio, as the core's plugin host runs it. |
| `scripts/rename.py` | Renames the example to your plugin in one step (see below). |
| `.github/workflows/ci.yml` | Lockfile, ruff, mypy (strict), pytest with an 85% coverage gate, gitleaks, and the aggregate **CI OK** check. In this repository only, **Template copy** also renames a copy of the template with `scripts/rename.py` and runs those checks on it. |
| `docs/authoring-checklist.md` | The [plugin authoring checklist](docs/authoring-checklist.md): permissions, secrets, untrusted input, recorded fixtures, degraded handling, docs and release. Go through it before each pull request and release. |
| `graft.yaml`, `AGENTS.md` | Review policy and the working rules for agents and humans. |

`horae-sdk` 0.6 (`>=0.6,<0.7`) is not on PyPI yet: `pyproject.toml` takes it from the core repository's `main`
branch (`[tool.uv.sources]`), and `uv.lock` pins the exact commit, so every build uses the
same SDK until the lock changes. Renovate's weekly lock file maintenance moves it to the latest
`main` (or run `uv lock --upgrade-package horae-sdk`); review that pull request like any
dependency bump. Installing it clones the core repository, which must stay public. Once
`horae-sdk` is published, delete that table: the requirement then resolves from PyPI.

## Use this template

1. **Create the repository**: "Use this template" on GitHub (or
   `gh repo create <owner>/<name> --template horae-dev/template-plugin`). CI runs on the first
   push and passes as is.
2. **Install**: `uv sync` (needs [uv](https://docs.astral.sh/uv/)), and optionally
   `uv run pre-commit install`.
3. **Rename** the example to your plugin, once, on the fresh copy:

   ```
   python3 scripts/rename.py <dist-name> <package> <plugin-name>
   # e.g. python3 scripts/rename.py horae-plugin-acme acme_plugin acme
   ```

   It renames `src/example_plugin/` and every reference (the distribution name and
   description in `pyproject.toml`, imports, the plugin's `NAME`, which is the namespace of
   its refs and fingerprints, the recordings, docstrings, the README and `AGENTS.md`
   titles), runs `uv lock`, regenerates `plugin.yaml` and re-records `tests/recordings`, then
   fails if a reference to the example is left. A plugin name matches `^[a-z][a-z0-9-]*$`; a
   ref is `<plugin-name>.<tool>`. Review `git diff` and commit.

   By hand, if you cannot run it: rename the package directory and its imports, `packages`
   in `pyproject.toml`, `source` in `[tool.coverage.run]`, the module in `COMMAND` and in the
   `--manifest` commands of this README and `AGENTS.md`; `name` in `pyproject.toml` and `NAME`
   in `plugin.py`; the `tool` and the fingerprints of each recording. Then run `uv lock` (CI's
   lockfile check fails otherwise: `uv.lock` records the project name), regenerate
   `plugin.yaml` (step 5) and re-record (step 6). `grep -rn example_plugin --exclude-dir=.venv .`
   and `grep -rn '"example' tests` find what is left.
4. **Write the plugin** in `plugin.py`: replace `Inbox` / `SampleInbox` with your service's
   client and the source with your tools. Read the
   [SDK README](https://github.com/horae-dev/horae/blob/main/sdk/README.md) for the roles,
   the intents and what is trusted. Declare the least you need in `PERMISSIONS`: every
   network host, secret, path and intent type. See [Building a plugin](#building-a-plugin)
   for the network, sink and test conventions.
5. **Regenerate the manifest**: `uv run python -m example_plugin --manifest > plugin.yaml`.
6. **Record fixtures**: put synthetic data in `tests/fixtures/`, one JSON file per call in
   `tests/recordings/` (`tool`, `params`, `input` for a transform, and `expect`), then
   `HORAE_SDK_RECORD=1 uv run pytest` writes the current outputs into `expect`. Review the diff
   before committing: what you commit is what CI checks. Include hostile inputs (Tasks
   signifiers, Markdown, links) for every untrusted field.
7. **Check your work** against the
   [authoring checklist](docs/authoring-checklist.md), then **run CI locally**, as CI does:

   ```
   uv lock --check
   uv run ruff check && uv run ruff format --check
   uv run mypy
   uv run pytest --cov
   ```

8. **Install it in Horae**: point the core at `plugin.yaml` with `runtime.command` pinned to
   an absolute interpreter that has your package installed (see "The command" in the SDK
   README).

## Building a plugin

Follow [CONTRIBUTING](https://github.com/horae-dev/marketplace) in the
[marketplace repository](https://github.com/horae-dev/marketplace) to publish a plugin and for
its review policy (the guide may still be in an open pull request: read it from the repository).
The conventions below are those of `horae-sdk` 0.6, as the first-party plugins use them.

**Network.** Declare every host in `permissions.network` (an `https` host name; no IP literal).
The core sends the hosts approved in `horae.lock` with every call, and the plugin asks before it
connects, with `call.host_allowed(url)` (a source or transform) or `request.host_allowed(url)`
(a sink's `apply`). Handle the three answers as the plugins do:

| Answer | Meaning | What to do |
|---|---|---|
| `True` | approved | go on |
| `False` | the lock does not approve it | refuse before any contact, naming the host and never the rest of the URL (it can hold a token): a skipped feed, or `SinkError("config_invalid", ...)` in a sink |
| `None` | an older core sent no list | go on: your own checks (declared hosts, parameters) stand, as before |

`host_refusal` in `plugin.py` is the pattern. For a protocol that is not HTTP (IMAP, SMTP) ask
`call.address_allowed(host, port)` the same way. A server on the local network or this machine
(a self-hosted service, a bridge on `127.0.0.1`) is not a `network` host: declare it as an exact
`host:port` in `permissions.network_local` (for example `127.0.0.1:1143` or `ntfy.lan:80`),
which the user approves in `horae.lock`; plain `http` is allowed on those endpoints only, and
`host_allowed` and `address_allowed` judge them by the exact host and port.

**A sink** (one that applies intents, such as a notifier or a note writer) provides the
operations `<ns>.read`, `apply`, `restore`, `restore_status`, `parent_exists` and `identity`.
These names are **reserved**: a source or transform may not use them as its ref. `restore`
takes a `force` keyword
(`restore(paths, path, content, expected_sha256, force=False)`; override it with that `force`
parameter, or mypy rejects the override) and `restore_status(paths, details, force=False)` is the
operation that undoes a `task.update_status` the sink applied. `force` is true only for
`horae undo --force`, the user's explicit choice, and never lifts the compare-and-swap. This example is a source and has no sink:
read `horae-sdk`'s `sinks` module, and `plugin-ntfy` for a notifier.

**The manifest** is generated, never written by hand: `uv run python -m example_plugin
--manifest > plugin.yaml`. `tests/test_manifest.py` rebuilds it from the file with the SDK's
checks (including `network_local`), requires it to equal what the code declares, and checks that
`--manifest` prints exactly the file. Regenerate it whenever tools or permissions change.

**Tests** use `horae_sdk.testing`: `replay_all` replays `tests/recordings`; `call(plugin, tool,
params, input=..., paths=..., network=..., network_local=...)` and `operation(...)` call a tool
or a sink operation as the core does. `network` is the list of approved hosts (`[]`: nothing
approved; `None`: an older core with no list) and `network_local` the approved `host:port`
endpoints. Test all three answers of `host_allowed`, and a local grant that matches, and one
that does not (`tests/test_network.py`). `HORAE_SDK_RECORD=1 uv run pytest` rewrites the
recordings and is refused in CI; a recording may also hold `network` and `network_local`.

## Contributing

This project is developed mostly by AI coding agents supervised by a human maintainer. Read
[AGENTS.md](AGENTS.md) for the workflow (it applies to humans too), and the organization's
[contributing guide](https://github.com/horae-dev/.github/blob/main/CONTRIBUTING.md) and
[security policy](https://github.com/horae-dev/.github/blob/main/SECURITY.md).

## License

[Apache-2.0](LICENSE)
