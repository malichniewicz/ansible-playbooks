# Copyright (c) 2025 Michał Alichniewicz
#
# This file is licensed under the MIT License.
# See the LICENSE file in the repository root for more information.

# Copyright (c) 2016 Red Hat Inc.
# Simplified BSD License (see LICENSES/BSD-2-Clause.txt or https://opensource.org/licenses/BSD-2-Clause)
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible.module_utils.common.text.converters import to_native
from ansible.module_utils.connection import Connection, ConnectionError
from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.utils import to_list


def get_connection(module):
    if hasattr(module, '_dlink_metro_connection'):
        return module._dlink_metro_connection

    capabilities = get_capabilities(module)
    network_api = capabilities.get('network_api')
    if network_api == 'cliconf':
        module._dlink_metro_connection = Connection(module._socket_path)
    else:
        module.fail_json(msg='Invalid connection type %s' % network_api)

    return module._dlink_metro_connection


def get_capabilities(module):
    if hasattr(module, '_dlink_metro_capabilities'):
        return module._dlink_metro_capabilities

    try:
        capabilities = Connection(module._socket_path).get_capabilities()
        module._dlink_metro_capabilities = json.loads(capabilities)
        return module._dlink_metro_capabilities
    except ConnectionError as exc:
        module.fail_json(msg=to_native(exc, errors='surrogate_then_replace'))


def run_commands(module, commands, check_rc=True):
    responses = list()
    connection = get_connection(module)

    for cmd in to_list(commands):
        if isinstance(cmd, dict):
            command = cmd['command']
            prompt = cmd['prompt']
            answer = cmd['answer']
        else:
            command = cmd
            prompt = None
            answer = None

        try:
            out = connection.get(command, prompt, answer)
        except ConnectionError as exc:
            module.fail_json(msg=to_native(exc, errors='surrogate_then_replace'))

        try:
            out = to_native(out, errors='surrogate_or_strict')
        except UnicodeError:
            module.fail_json(
                msg=u'Failed to decode output from %s: %s' % (cmd, to_native(out)))

        responses.append(out)

    return responses
