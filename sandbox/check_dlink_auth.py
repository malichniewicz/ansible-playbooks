from ansible_vault import Vault
import ansible.errors
import yaml
import getpass
import os
import hashlib
import requests
import logging
import re
import json


def pythonize_value(value: str):
    def _parse_list(input_str):
        input_str = input_str.replace('\n', '').replace('\r', '').strip()

        def _parse_helper(index):
            result = []
            current_value = ""
            while index < len(input_str):
                char = input_str[index]
                if char == '[':  # Start of a new sublist
                    sublist, index = _parse_helper(index + 1)
                    result.append(sublist)
                elif char == ']':  # End of current list
                    if current_value:
                        result.append(pythonize_value(current_value))
                    return result, index
                elif char == ',':  # Separator
                    if current_value:
                        result.append(pythonize_value(current_value))
                        current_value = ""
                else:
                    current_value += char
                index += 1

            return result, index

        parsed, _ = _parse_helper(0)
        
        return parsed[0] if len(parsed) == 1 and isinstance(parsed[0], list) else parsed

    value = value.strip()
    # print(f'VALUE: {repr(value)}')
    if value.startswith('[') and value.endswith(']'):
        # It's a list
        return _parse_list(value)
    elif (value.startswith('\'') or value.startswith('"')) and (value.endswith('\'') or value.endswith('"')):
        # It's most likely a string
        return value[1:-1]
    elif value.lower() == 'null':
        # It's null
        return None
    elif value.lower() == 'true' or value.lower() == 'false':
        # It's bool
        return bool(value)
    elif '.' in value:
        # It's a float
        return float(value)
    else:
        # It's a number
        return int(value)

switch_name = 'switch-03'

root_dir = os.path.abspath(os.path.join(os.path.basename(__file__), '..'))
vault_pass_file = os.path.join(root_dir, '.vaultpass')
secrets_file = os.path.join(root_dir, 'inventory', 'host_vars', switch_name, 'vault.yml')
inventory_file = os.path.join(root_dir, 'inventory', 'infrastructure.yml')

login_cookie_regex = re.compile(r"document\.cookie='(.*)';")
api_response_path_regex = re.compile(r"<script>RT='/(.*)/';</script>")

# Load inventory
with open(inventory_file, 'r', encoding='utf-8') as fp:
    inventory = yaml.load(fp.read(), Loader=yaml.SafeLoader)

host = inventory['infrastructure']['hosts'][switch_name]['ansible_host']

try:
    # Load password from the ansible vault file
    with open('.vaultpass', 'r', encoding='utf-8') as fp:
        vault_pass = fp.read()
except FileNotFoundError:
    # Password file not found, ask the user    
    vault_pass = getpass.getpass()

with open(secrets_file, 'r', encoding='utf-8') as fp:
    content = fp.read()
    try:
        secrets = Vault(vault_pass).load(content)
    except ansible.errors.AnsibleError:
        # file is probably not encrypted, e.g. during development stage
        secrets = yaml.load(content, Loader=yaml.SafeLoader)

# Get main page to get the API path
resp = requests.get(f'http://{host}/')
api_response_path = api_response_path_regex.findall(resp.content.decode())[0]

# Try to authenticate to switch
password_encoded = hashlib.md5(secrets['default_password'].encode()).hexdigest()
login_endpoint = f'http://{host}/cgi/login.cgi'

headers = {
    'Referer': f'http://{host}/'  # Required to get the cookie
}

resp = requests.post(login_endpoint, data={'pass': password_encoded}, headers=headers)

cookies = {}
for parsed_cookie in login_cookie_regex.findall(resp.content.decode()):
    cookie_data = parsed_cookie.split(';')[0].split('=')
    cookies[cookie_data[0]] = ''.join(cookie_data[1:]) # In some cases, cookie data may contain "=" character

resp = requests.get(f'http://{host}/{api_response_path}/DS/const.js', cookies=cookies, headers=headers)
print(f"\nHTTP CODE {resp.status_code}")
print("---")
print(resp.content.decode())

vars_regex = re.compile(r"var (?P<name>[^=]+) *= *(?P<value>[^;]*);\n", re.MULTILINE)
vars = {}
for item in vars_regex.finditer(resp.content.decode()):
    # print(item.group('name'), item.group('value'))
    vars[item.group('name').strip()] = pythonize_value(item.group('value').strip())

print(repr(vars))
# print(vars['g_DftOUITable'])