# Copyright (c) 2025 Michał Alichniewicz
#
# This file is licensed under the MIT License.
# See the LICENSE file in the repository root for more information.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re

from ansible.errors import AnsibleConnectionFailure
from ansible_collections.ansible.netcommon.plugins.plugin_utils.terminal_base import \
    TerminalBase


class TerminalModule(TerminalBase):
    terminal_stdout_re = [
        re.compile(rb"DGS-\d{4}-\d{2}/ME:\d#"),
    ]

    terminal_stderr_re = [
        re.compile(rb"Available commands:"),
        re.compile(rb"Next possible completions:"),
    ]

    terminal_config_prompt = re.compile(r"^.+#$")

    def on_open_shell(self):
        try:
            # Disable paging. If not set, then D-Link switch may return only part of the
            # response followed by prompt what to do next, e.g.
            #   CTRL+C ESC q Quit SPACE n Next Page ENTER Next Entry a ALL
            # This flag have to be set once and is persistent, however we cannot rely
            # that this is present and we want to be sure.
            self._exec_cli_command('disable clipaging')
        except AnsibleConnectionFailure:
            raise AnsibleConnectionFailure('unable to set terminal parameters')