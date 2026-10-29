# SPDX-License-Identifier: Apache-2.0
"""Rename the template's example plugin to yours, in one step.

    python3 scripts/rename.py <dist-name> <package> <plugin-name>
    python3 scripts/rename.py horae-plugin-acme acme_plugin acme

It renames the package directory (`src/example_plugin`) and every reference to it: the
distribution name and description in `pyproject.toml`, the imports, the plugin's `NAME` (the
namespace of its refs and fingerprints), the recordings' `tool` and fingerprints, docstrings,
and the README and AGENTS.md titles. Then it runs `uv lock` (uv.lock records the project
name), regenerates `plugin.yaml` with `--manifest`, and re-records `tests/recordings`
(`HORAE_SDK_RECORD=1 uv run pytest`) so you can review their diff. Record mode is refused in
CI, so there the re-recording is skipped and the replayed tests check the rewritten
recordings as they are. Finally it fails if any reference to the example is left.

Run it once, on a fresh copy of the template, then review `git diff`. Standard library only.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD_DIST = "horae-plugin-example"
OLD_PACKAGE = "example_plugin"
OLD_NAME = "example"

DIST_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PACKAGE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")  # a Horae plugin name

SKIP_DIRS = {".git", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
# Not rewritten as text: the license is the verbatim Apache-2.0 text, uv.lock is regenerated
# by `uv lock`, and this script must keep naming the example.
SKIP_FILES = {"LICENSE", "uv.lock", "scripts/rename.py"}
TEXT_SUFFIXES = {".py", ".toml", ".md", ".yaml", ".yml", ".json", ".txt", ".cfg", ".ini"}
CI_ENVS = ("CI", "GITHUB_ACTIONS")  # where horae_sdk.testing refuses record mode

RESERVED_TLDS = r"(?:com|net|org)\b"  # RFC 2606: example.com etc. stay as they are
# A leftover reference: the package, the distribution, a ref or a fingerprint of the example.
LEFTOVER = re.compile(
    rf"{OLD_PACKAGE}|{OLD_DIST}|NAME = \"{OLD_NAME}\""
    rf"|\b{OLD_NAME}\.(?!{RESERVED_TLDS})[a-z]|\b{OLD_NAME}:"
)


def replacements(dist: str, package: str, name: str) -> list[tuple[re.Pattern[str], str]]:
    """Ordered: the longer names first, then the plugin name where it is an identifier."""
    pairs = [
        (re.escape(OLD_DIST), dist),
        (re.escape(OLD_PACKAGE), package),
        (rf'NAME = "{OLD_NAME}"', f'NAME = "{name}"'),
        # refs (`example.inbox`) and fingerprints (`example:reply:m-1`); not `.env.example`
        # nor the reserved example domains of the fixtures (`https://example.org`)
        (rf"\b{OLD_NAME}\.(?!{RESERVED_TLDS})(?=[a-z])", f"{name}."),
        (rf"\b{OLD_NAME}:(?=[a-z])", f"{name}:"),
        # descriptions and docstrings
        (r"\bAn example Horae plugin\b", f"The {name} Horae plugin"),
        (r"\ban example Horae plugin\b", f"the {name} Horae plugin"),
        (r" \(rename the package, the plugin and its refs to make it yours\)", ""),
        # titles
        (r"^# template-plugin$", f"# {dist}"),
        (
            r"^# AGENTS\.md — how to work in `template-plugin`$",
            f"# AGENTS.md — how to work in `{dist}`",
        ),
    ]
    return [(re.compile(old, re.MULTILINE), new) for old, new in pairs]


def text_files(root: Path) -> list[Path]:
    found = []
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for file in sorted(files):
            path = Path(directory, file)
            relative = path.relative_to(root).as_posix()
            if relative in SKIP_FILES or path.is_symlink():
                continue
            if path.suffix in TEXT_SUFFIXES or file.startswith("."):
                found.append(path)
    return found


def rewrite(root: Path, rules: list[tuple[re.Pattern[str], str]]) -> list[str]:
    changed = []
    for path in text_files(root):
        try:
            before = path.read_text("utf-8")
        except UnicodeDecodeError:
            continue
        after = before
        for pattern, new in rules:
            after = pattern.sub(new, after)
        if after != before:
            path.write_text(after, "utf-8")
            changed.append(path.relative_to(root).as_posix())
    return changed


def leftovers(root: Path) -> list[str]:
    found = []
    for path in text_files(root):
        try:
            lines = path.read_text("utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            if LEFTOVER.search(line):
                found.append(f"{path.relative_to(root).as_posix()}:{number}: {line.strip()}")
    return found


def run(args: list[str], env: dict[str, str] | None = None, stdout: int | None = None) -> bytes:
    print("+", " ".join(args), file=sys.stderr)
    result = subprocess.run(args, cwd=ROOT, env=env, stdout=stdout, check=True)  # noqa: S603
    return result.stdout or b""


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dist", help="distribution name, e.g. horae-plugin-acme")
    parser.add_argument("package", help="Python package, e.g. acme_plugin")
    parser.add_argument("name", help="plugin name, the namespace of its refs, e.g. acme")
    args = parser.parse_args(argv)
    for value, pattern, what in (
        (args.dist, DIST_RE, "dist-name"),
        (args.package, PACKAGE_RE, "package"),
        (args.name, NAME_RE, "plugin-name"),
    ):
        if not pattern.match(value):
            parser.error(f"{what} {value!r} must match {pattern.pattern}")
    if not args.package.isidentifier():
        parser.error(f"package {args.package!r} is not a Python identifier")

    old_dir, new_dir = ROOT / "src" / OLD_PACKAGE, ROOT / "src" / args.package
    if not old_dir.is_dir():
        sys.exit(f"{old_dir} not found: already renamed?")
    if new_dir.exists():
        sys.exit(f"{new_dir} already exists")
    uv = shutil.which("uv")
    if uv is None:
        sys.exit("uv not found: install it first (https://docs.astral.sh/uv/)")

    shutil.move(old_dir, new_dir)
    changed = rewrite(ROOT, replacements(args.dist, args.package, args.name))
    print(f"renamed src/{OLD_PACKAGE} -> src/{args.package}; rewrote {len(changed)} files:")
    for path in changed:
        print(f"  {path}")

    env = {k: v for k, v in os.environ.items() if k not in {"UV_LOCKED", "UV_FROZEN"}}
    run([uv, "lock"], env=env)
    manifest = run([uv, "run", "python", "-m", args.package, "--manifest"], stdout=subprocess.PIPE)
    (ROOT / "plugin.yaml").write_bytes(manifest)

    in_ci = [name for name in CI_ENVS if os.environ.get(name)]
    if in_ci:
        print(f"{', '.join(in_ci)} set: not re-recording (refused in CI); replay checks them as is")
    else:
        run([uv, "run", "pytest", "-q"], env=env | {"HORAE_SDK_RECORD": "1"})

    left = leftovers(ROOT)
    if left:
        print("references to the example are left; rename them by hand:", *left, sep="\n  ")
        sys.exit(1)
    print(
        "done: review `git diff`, then write your plugin in "
        f"src/{args.package}/plugin.py (see the README). LICENSE is Apache-2.0 with no named "
        "holder; add a copyright line or NOTICE file if you want one."
    )


if __name__ == "__main__":
    main(sys.argv[1:])
