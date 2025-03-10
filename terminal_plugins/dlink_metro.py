from __future__ import absolute_import, division, print_function


__metaclass__ = type

import os
import re

from ansible.errors import AnsibleConnectionFailure
from ansible_collections.ansible.netcommon.plugins.plugin_utils.terminal_base import TerminalBase


class TerminalModule(TerminalBase):
    terminal_stdout_re = [
        re.compile(rb"DGS-\d{4}-\d{2}/ME:\d#"),
    ]

    terminal_stderr_re = [
        re.compile(rb"Available commands:"),
        re.compile(rb"Next possible completions:"),
    ]

    terminal_config_prompt = re.compile(r"^.+#$")

    def _exec_cli_command(self, cmd, check_rc=True):
        """
        Executes the CLI command on the remote device and returns the output

        :arg cmd: Byte string command to be executed
        """
        # TODO: handle paged output
        retcode, stderr, stdout = self._connection.exec_command(cmd)
        if b'CTRL+C ESC q Quit SPACE n Next Page ENTER Next Entry a ALL' in stdout:
            self._connection.exec_command(b'q')
        return retcode, stderr, stdout