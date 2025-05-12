# source: https://stackoverflow.com/questions/69036942/ansible-create-sha512-pbkdf2-hash
#
# This file is licensed under the CC-BY-SA-4.0 License.
# Visit https://creativecommons.org/licenses/by-sa/4.0/ for more informations.
#
# SPDX-License-Identifier: CC-BY-SA-4.0
from ansible.errors import AnsibleError


def mosquitto_passwd(passwd):
    try:
        import passlib.hash
    except Exception as e:
        raise AnsibleError('to use this filter, you need passlib pip package installed')
    SALT_SIZE = 12
    ITERATIONS = 101

    digest = passlib.hash.pbkdf2_sha512.using(salt_size=SALT_SIZE, rounds=ITERATIONS)\
                                        .hash(passwd) \
                                        .replace('pbkdf2-sha512', '7') \
                                        .replace('.', '+')

    return digest + '=='


class FilterModule(object):
    def filters(self):
        return {
            'mosquitto_passwd': mosquitto_passwd,
        }
