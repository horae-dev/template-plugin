# SPDX-License-Identifier: Apache-2.0
"""The plugin: one source, `example.inbox`, that proposes a task per message.

The core's plugin host starts this module as an MCP server over stdio (`python -m
example_plugin`). The plugin never writes anything: it returns data and proposes intents,
which the core checks against `plugin.yaml`'s permissions, shows as a dry-run diff and
applies.

A message comes from a service the plugin does not control, so its fields are **untrusted**:
the subject reaches the task title only through `intents.task_create`, which escapes it for
Obsidian Tasks (a subject holding `📅 2020-01-01` must not schedule the task).
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol
from urllib.parse import urlsplit

from horae_sdk import Call, Output, Permissions, Plugin, intents

NAME = "example"
"""The plugin's name, also the namespace of its refs (`example.inbox`) and fingerprints."""
VERSION = "0.1.0"
HORAE = ">=0,<0.2"
"""`horae` of `plugin.yaml`: the core versions this plugin is written for."""
COMMAND = ["python3", "-m", "example_plugin"]
"""`runtime.command` of `plugin.yaml`. When installing, pin an absolute interpreter that has
this package (the host's `PATH` is fixed and its working directory empty)."""
PERMISSIONS = Permissions(intents=["task.create"])
"""Declare the least you need: every network host, secret, path and intent type."""

Allows = Callable[[str], bool | None]
"""`Call.host_allowed` / `ApplyRequest.host_allowed`: `True` when the core approves the URL
(an `https` URL on a host of `permissions.network`, or an `http(s)` URL on an exact `host:port`
of `permissions.network_local`), `False` when it does not, `None` when the core is older and sent
no list (the plugin's own checks then stand)."""


def host_refusal(allows: Allows, url: str) -> str | None:
    """The reason to refuse `url` before contacting it, or `None` to go ahead.

    This example reads no network (its `PERMISSIONS` declare none), so nothing calls it; it
    shows how a plugin that does handles the three answers of `host_allowed`: only `False` is a
    refusal, `True` and `None` go on. It names the host, never the rest of the URL (which can
    hold a token). For a protocol that is not HTTP (IMAP, SMTP), ask
    `call.address_allowed(host, port)` the same way."""
    if allows(url) is False:
        return f"host_not_approved: {urlsplit(url).hostname}"
    return None


class Inbox(Protocol):
    """Where the messages come from. Replace it with your service's client; the tests give the
    plugin a fake one that answers from synthetic fixtures."""

    def messages(self, folder: str) -> Sequence[Mapping[str, Any]]:
        """The messages of `folder`, each a mapping with at least `id` and `subject`."""
        ...


class SampleInbox:
    """A stand-in client with one synthetic message, so the plugin runs as shipped."""

    def messages(self, folder: str) -> Sequence[Mapping[str, Any]]:
        return [{"id": "welcome", "subject": f"Welcome to {folder}"}]


def build(inbox: Inbox) -> Plugin:
    """The plugin, reading its messages from `inbox`."""
    plugin = Plugin(
        NAME,
        version=VERSION,
        permissions=PERMISSIONS,
        description="Proposes a task to reply to each message of a folder.",
    )

    @plugin.source(f"{NAME}.inbox")
    def inbox_source(call: Call, folder: str = "inbox") -> Output:
        # `folder` is a pipeline parameter (trusted); every message field is untrusted data.
        seen: list[dict[str, str]] = []
        tasks: list[dict[str, Any]] = []
        for message in inbox.messages(folder):
            message_id, subject = message.get("id"), message.get("subject")
            if not isinstance(message_id, str) or not isinstance(subject, str):
                continue
            seen.append({"id": message_id, "subject": subject})
            key = intents.fingerprint(NAME, "reply", message_id)
            tasks.append(intents.task_create(f"Reply to {subject}", key=key))
        return Output({"folder": folder, "messages": seen}, intents=tasks)

    return plugin


def manifest() -> dict[str, Any]:
    """The `plugin.yaml` document of this plugin (`python -m example_plugin --manifest`)."""
    return build(SampleInbox()).manifest(command=COMMAND, horae=HORAE, license="Apache-2.0")
