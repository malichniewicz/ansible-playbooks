# Copyright (c) 2025 Michał Alichniewicz
#
# This file is licensed under the MIT License.
# See the LICENSE file in the repository root for more information.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import re

from ansible.module_utils.common.text.converters import to_text
from ansible.plugins.cliconf import CliconfBase


class Cliconf(CliconfBase):

    def get_device_info(self):
        device_info = {}
        device_info['network_os'] = 'D-Link/ME'

        resource = self.get('show switch')
        data = to_text(resource, errors='surrogate_or_strict').strip()
        version_match = re.search(r'System Firmware Version *: (.*)', data, re.MULTILINE)
        if version_match:
            device_info['network_os_version'] = version_match.group(1)
        
        model_match = re.search(r'Device Type *: (.*)', data, re.MULTILINE)
        if model_match:
            device_info['network_os_model'] = model_match.group(1)

        hostname_match = re.search(r'System Name *: (.*)', data, re.MULTILINE)
        if hostname_match:
            device_info['network_os_hostname'] = hostname_match.group(1)

        return device_info

    def get_config(self, source='running', flags=None, format=None):
        return

    def edit_config(self, command):
        return

    def get(self, command, prompt=None, answer=None, sendonly=False, newline=True, check_all=False):
        return self.send_command(command=command, prompt=prompt, answer=answer, sendonly=sendonly, newline=newline, check_all=check_all)

    def get_capabilities(self):
        result = super(Cliconf, self).get_capabilities()
        return json.dumps(result)