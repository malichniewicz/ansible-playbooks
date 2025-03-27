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

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems
from ansible_collections.local.dlink.plugins.module_utils.metro import \
    run_commands


class FactsBase(object):

    COMMANDS = list()

    def __init__(self, module):
        self.module = module
        self.facts = dict()
        self.responses = None

    def populate(self):
        self.responses = run_commands(self.module, commands=self.COMMANDS, check_rc=False)

    def run(self, cmd):
        return run_commands(self.module, commands=cmd, check_rc=False)


class Default(FactsBase):

    COMMANDS = [
        'show switch',
    ]

    def populate(self):
        super(Default, self).populate()
        data = self.responses[0]
        if data:
            self.facts['hostname'] = self.parse_hostname(data)
            self.facts['version'] = self.parse_version(data)
            self.facts['uptime'] = self.parse_uptime(data)
            self.facts['model'] = self.parse_model(data)
            self.facts['serialnum'] = self.parse_serialnum(data)

    def parse_hostname(self, data):
        match = re.search(r'^System Name\s*:\s*(.+)$', data, re.M)
        if match:
            return match.group(1)

    def parse_version(self, data):
        match = re.search(r'^System Firmware Version\s*:\s*(.+)*$', data, re.M)
        if match:
            return match.group(1)

    def parse_model(self, data):
        match = re.search(r'^Device Type\s*:\s*(.+)$', data, re.M)
        if match:
            return match.group(1)

    def parse_uptime(self, data):
        match = re.search(r'^System up time\s*:\s*(.+)$', data, re.M)
        if match:
            return match.group(1)

    def parse_serialnum(self, data):
        match = re.search(r'^System Serial Number\s*:\s*(.+)$', data, re.M)
        if match:
            return match.group(1)


class Config(FactsBase):

    COMMANDS = [
        'show config current_config',
    ]

    def populate(self):
        super(Config, self).populate()

        data = self.responses[0]
        if data:
            match = re.search(r'^Command: show config current_config\n\n(.*)', data, re.S)
            if match:
                self.facts['config'] = match.group(1)

class Hardware(FactsBase):
    COMMANDS = [
        'show flash information',
        # Command: show flash information

        # Flash ID    : MX25L25635E
        # Flash size  : 32MB

        # Partition      Used           Available      Use%
        # Boot           1310720        0              0
        # Image1         13471776       684000         95
        # Image2         12701728       1454048        89
        # FileSystem     323584         3608576        8
        'top',
        # Command: top
        # Mem: 108880K used, 2204K free, 0K shrd, 5456K buff, 27804K cached
        # CPU:  3.4% usr  6.8% sys  0.0% nic 37.9% idle  0.0% io  0.0% irq 51.7% sirq
        # Load average: 1.79 1.66 1.61 2/123 690
        # ...
    ]

    def populate(self):
        super(Hardware, self).populate()
        data = self.responses[0]
        if data:
            self.facts['flash_id'] = self.parse_flash_id(data)
            self.facts['flash'] = self.parse_flash_details(data)

    def parse_flash_id(self, data):
        match = re.search(r'^Flash ID\s*:\s*(.+)$', data, re.M)
        if match:
            return match.group(1)

    def parse_flash_details(self, data):
        header_found = False
        flash_data = {}
        for line in data.splitlines():
            if header_found:
                partition_details = line.split()
                if len(partition_details) == 4:
                    # Entry like
                    # Boot           1310720        0              0
                    flash_data[partition_details[0]] = {
                        'used_bytes': int(partition_details[1]),
                        'available_bytes': int(partition_details[2]),
                        'total_bytes': int(partition_details[1]) + int(partition_details[2])
                    }
            elif re.match(r'^Partition\s*Used\s*Available\s*Use%\s*', line):
                header_found = True
        return flash_data

    def parse_memfree(self, data):
        pass

    def parse_memtotal(self, data):
        pass

    def parse_cpu_load(self, data):
        pass

FACT_SUBSETS = dict(
    default=Default,
    config=Config,
    hardware=Hardware
)

VALID_SUBSETS = frozenset(FACT_SUBSETS.keys())

warnings = list()


def main():
    argument_spec = dict(
        gather_subset=dict(default=['!config'], type='list', elements='str')
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=True)

    gather_subset = module.params['gather_subset']

    runable_subsets = set()
    exclude_subsets = set()

    for subset in gather_subset:
        if subset == 'all':
            runable_subsets.update(VALID_SUBSETS)
            continue

        if subset.startswith('!'):
            subset = subset[1:]
            if subset == 'all':
                exclude_subsets.update(VALID_SUBSETS)
                continue
            exclude = True
        else:
            exclude = False

        if subset not in VALID_SUBSETS:
            module.fail_json(msg='Bad subset: %s' % subset)

        if exclude:
            exclude_subsets.add(subset)
        else:
            runable_subsets.add(subset)

    if not runable_subsets:
        runable_subsets.update(VALID_SUBSETS)

    runable_subsets.difference_update(exclude_subsets)
    runable_subsets.add('default')

    facts = dict()
    facts['gather_subset'] = list(runable_subsets)

    instances = list()
    for key in runable_subsets:
        instances.append(FACT_SUBSETS[key](module))

    for inst in instances:
        inst.populate()
        facts.update(inst.facts)

    ansible_facts = dict()
    for key, value in iteritems(facts):
        key = 'ansible_net_%s' % key
        ansible_facts[key] = value

    module.exit_json(ansible_facts=ansible_facts, warnings=warnings)


if __name__ == '__main__':
    main()