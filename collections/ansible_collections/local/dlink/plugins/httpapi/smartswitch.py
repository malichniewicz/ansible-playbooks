# Copyright (c) 2025 Michał Alichniewicz
#
# This file is licensed under the MIT License.
# See the LICENSE file in the repository root for more information.
#
# SPDX-License-Identifier: MIT

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import hashlib
import json
import re
from urllib import parse as urllib_parse

from ansible.errors import AnsibleAuthenticationFailure
from ansible_collections.ansible.netcommon.plugins.plugin_utils.httpapi_base import \
    HttpApiBase


class HttpApi(HttpApiBase):
    def __init__(self, connection):
        super().__init__(connection)

        self._device_info = None
    
    def send_request(self, data, path, method='POST'):
        # Fixed headers for requests
        # Referer header is required for proper request handle - if it is not present, then
        # switch will redirect to the main page
        headers = {
            'Referer': f'http://{self.connection.get_option("host")}/'  # Required to get the cookie
        }

        response, response_stream = self.connection.send(path, data, method=method, headers=headers)
        response_content = response_stream.read().decode()

        resp_content_type = response.headers.get("Content-Type")

        # TODO: Handle in more elegant way
        if "application/x-javascript" in resp_content_type:
            return handle_response_js(response_content)
        else:
            return response_content
    
    def login(self, username, password):
        login_cookie_regex = re.compile(r"document\.cookie='(.*)';")

        # Try to authenticate to switch - username is not used
        # The switch requires to provide password as an url-encoded "pass" form element, with MD5 hash of password
        # as a value
        password_encoded = hashlib.md5(password.encode()).hexdigest()
        request_data = urllib_parse.urlencode({'pass': password_encoded})
        resp = self.send_request(request_data, '/cgi/login.cgi')

        if 'loginerr.js' in resp:
            # Something went wrong with the login - probably invalid password
            raise AnsibleAuthenticationFailure('Invalid login or password')

        cookies = {}
        for parsed_cookie in login_cookie_regex.findall(resp):
            cookie_data = parsed_cookie.split(';')[0].split('=')
            cookies[cookie_data[0].strip()] = ''.join(cookie_data[1:]) # In some cases, cookie data 
                                                                       # may contain "=" character
        
        # Prepare cookies for authetication - it looks like the switch just looks for a "Gambit=XXX" string
        # in the Cookie header, so we don't bother in any string escaping - as the switch does.
        cookie_string = '; '.join(f'{key}={value}' for key,value in cookies.items())
        self.connection._auth = {'Cookie': cookie_string}

    def get_device_info(self):
        if self._device_info:
            return self._device_info

        api_response_path_regex = re.compile(r"<script>RT='/(.*)/';</script>")
        device_info = {}

        device_info["network_os"] = "smartswitch"
    
        # Get main page to get the API path
        resp = self.send_request(None, '/', method='GET')
        device_info["api_response_path"] = api_response_path_regex.findall(resp)[0]

        self._device_info = device_info

        return self._device_info

    def get_capabilities(self):
        result = {}
        result["rpc"] = []
        result["network_api"] = "httpapi"
        result["device_info"] = self.get_device_info()

        return json.dumps(result)

    def get(self, path: str, *, skip_extra_path=False):
        # Unify the path
        if not path.startswith('/'):
            path = '/' + path
        
        # Add the extra part required by switch to the request PATH
        if not skip_extra_path:
            extra_path = self.get_device_info().get('api_response_path')
            path = '/' + extra_path + path

        response = self.send_request(None, path, method='GET')

        return response


def _js_to_python(value: str):
    """ Simple parser of JS variables """
    def _parse_list(input_str):
        """ Convert JS list to Python list """
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
                        result.append(_js_to_python(current_value))
                    return result, index
                elif char == ',':  # Separator
                    if current_value:
                        result.append(_js_to_python(current_value))
                        current_value = ""
                else:
                    current_value += char
                index += 1

            return result, index

        parsed, _ = _parse_helper(0)
        
        return parsed[0] if len(parsed) == 1 and isinstance(parsed[0], list) else parsed

    value = value.strip()
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

def handle_response_js(response):
    vars_regex = re.compile(r"var (?P<name>[^=]+) *= *(?P<value>[^;]*);\n", re.MULTILINE)
    vars = {}
    
    for item in vars_regex.finditer(response):
        vars[item.group('name').strip()] = _js_to_python(item.group('value').strip())

    return vars