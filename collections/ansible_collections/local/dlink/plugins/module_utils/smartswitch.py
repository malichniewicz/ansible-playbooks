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
    if hasattr(module, '_dlink_smartswitch_connection'):
        return module._dlink_smartswitch_connection

    capabilities = get_capabilities(module)
    network_api = capabilities.get('network_api')
    if network_api == 'httpapi':
        module._dlink_smartswitch_connection = Connection(module._socket_path)
    else:
        module.fail_json(msg='Invalid connection type %s' % network_api)

    return module._dlink_smartswitch_connection

def get_capabilities(module):
    if hasattr(module, '_dlink_smartswitch_capabilities'):
        return module._dlink_smartswitch_capabilities

    try:
        capabilities = Connection(module._socket_path).get_capabilities()
        module._dlink_smartswitch_capabilities = json.loads(capabilities)
        return module._dlink_smartswitch_capabilities
    except ConnectionError as exc:
        module.fail_json(msg=to_native(exc, errors='surrogate_then_replace'))