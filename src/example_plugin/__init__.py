# SPDX-License-Identifier: Apache-2.0
"""An example Horae plugin (rename the package, the plugin and its refs to make it yours)."""

from example_plugin.plugin import COMMAND, NAME, Inbox, SampleInbox, build, manifest

__all__ = ["COMMAND", "NAME", "Inbox", "SampleInbox", "build", "manifest"]
