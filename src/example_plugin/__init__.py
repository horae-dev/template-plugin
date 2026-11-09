# SPDX-License-Identifier: Apache-2.0
"""An example Horae plugin (rename the package, the plugin and its refs to make it yours)."""

from example_plugin.plugin import (
    COMMAND,
    HORAE,
    NAME,
    Inbox,
    SampleInbox,
    build,
    host_refusal,
    manifest,
)

__all__ = [
    "COMMAND",
    "HORAE",
    "NAME",
    "Inbox",
    "SampleInbox",
    "build",
    "host_refusal",
    "manifest",
]
