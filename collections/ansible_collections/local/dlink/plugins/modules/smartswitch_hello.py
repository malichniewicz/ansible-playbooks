#!/usr/bin/python

# Copyright (c) 2025 Michał Alichniewicz
#
# This file is licensed under the MIT License.
# See the LICENSE file in the repository root for more information.
#
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re
from urllib import parse as urllib_parse

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems
from ansible_collections.local.dlink.plugins.module_utils.smartswitch import \
    get_connection


warnings = list()


def main():
    argument_spec = dict()

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    connection = get_connection(module)

    response = connection.get('/DS/Switch.js')

    module.exit_json(foo=response, warnings=warnings)


if __name__ == '__main__':
    main()