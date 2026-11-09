# SPDX-License-Identifier: Apache-2.0
"""What the core approved in `horae.lock` reaches the plugin as `Call.host_allowed`: the SDK's
`call(..., network=..., network_local=...)` plays the core. `network=None` is a core older than
horae-sdk 0.5, which sent no list; an empty `network` is a core that approved nothing."""

from collections.abc import Sequence

import anyio
import pytest
from horae_sdk import Call, Output, Plugin
from horae_sdk.testing import call

from example_plugin import host_refusal

TOOL = "probe.verdict"
HTTPS = "https://mail.example.org/"
LAN = "http://mail.lan:8080/"


def probe() -> Plugin:
    """A throwaway source that reports the verdicts of `host_allowed` and `address_allowed`."""
    plugin = Plugin("probe")

    @plugin.source(TOOL)
    def verdict(call: Call) -> Output:
        return Output(
            {
                "https": call.host_allowed(HTTPS),
                "lan": call.host_allowed(LAN),
                "imap": call.address_allowed("mail.lan", 1143),
                "refusal": host_refusal(call.host_allowed, HTTPS),
            }
        )

    return plugin


def ask(
    network: Sequence[str] | None, network_local: Sequence[str] | None = None
) -> dict[str, object]:
    async def go() -> dict[str, object]:
        replayed = await call(probe(), TOOL, network=network, network_local=network_local)
        assert isinstance(replayed.data, dict)
        return replayed.data

    return anyio.run(go)


def test_an_approved_https_host_is_true() -> None:
    assert ask(["mail.example.org"])["https"] is True


def test_a_host_the_lock_does_not_hold_is_false() -> None:
    data = ask([])
    assert data["https"] is False
    assert data["refusal"] == "host_not_approved: mail.example.org"


def test_no_list_at_all_is_none_and_not_a_refusal() -> None:
    data = ask(None)
    assert data["https"] is None
    assert data["lan"] is None
    assert data["imap"] is None
    assert data["refusal"] is None


@pytest.mark.parametrize(
    ("network_local", "lan", "imap"),
    [
        (["mail.lan:8080"], True, False),  # an exact host:port, over plain http
        (["mail.lan:1143"], False, True),  # another port: not the URL's, but the IMAP one
        (["mail.lan:80"], False, False),
        ([], False, False),
    ],
)
def test_a_local_endpoint_needs_its_exact_host_and_port(
    network_local: list[str], lan: bool, imap: bool
) -> None:
    data = ask([], network_local)
    assert data["lan"] is lan
    assert data["imap"] is imap
