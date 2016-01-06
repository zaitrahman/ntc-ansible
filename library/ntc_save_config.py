#!/usr/bin/env python

# Copyright 2015 Jason Edelman <jason@networktocode.com>
# Network to Code, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DOCUMENTATION = '''
---
module: ntc_save_config
short_description: Save the running config locally and/or remotely.
description:
    - Save the running configuration as the startup configuration or to a file on the network device.
      Optionally, save the running configuration to this computer.
    - Supported platforms: Cisco Nexus switches with NX-API; Arista switches with eAPI.
notes:
    - This module is not idempotent.
author: Jason Edelman (@jedelman8)
version_added: 1.9.2
requirements:
    - pyntc
options:
    platform:
        description:
            - Vendor and platform identifier.
        required: true
        choices: ['cisco_nxos_nxapi', 'cisco_ios', 'arista_eos_eapi']
    remote_file:
        description:
            - Name of remote file to save the running configuration. If omitted it will be
              saved to the startup configuration.
        required: false
        default: null
    local_file:
        description:
            - Name of local file to save the running configuration. If omitted it won't be locally saved.
        required: false
        default: null
    host:
        description:
            - Hostame or IP address of switch.
        required: true
    username:
        description:
            - Username used to login to the target device.
        required: true
    password:
        description:
            - Password used to login to the target device.
        required: true
    secret:
        description:
            - Enable secret for devices connecting over SSH.
        required: false
    transport:
        description:
            - Transport protocol for API. Only needed for NX-API and eAPI.
              If omitted, platform-specific default will be used.
        required: false
        default: null
        choices: ['http', 'https']
    port:
        description:
            - TCP/UDP port to connect to target device. If omitted standard port numbers will be used.
              80 for HTTP; 443 for HTTPS; 22 for SSH.
        required: false
        default: null
'''

EXAMPLES = '''
- ntc_save_config:
    platform: cisco_nxos_nxapi
    host: "{{ inventory_hostname }}"
    username: "{{ username }}"
    password: "{{ password }}"

- ntc_save_config:
    platform: arista_eos_eapi
    host: "{{ inventory_hostname }}"
    username: "{{ username }}"
    password: "{{ password }}"
    remote_file: running_config_copy.cfg
    transport: https

# You can get the timestamp by setting get_facts to True, then you can append it to your filename.

- ntc_save_config:
    platform: cisco_ios
    host: "{{ inventory_hostname }}"
    username: "{{ username }}"
    password: "{{ password }}"
    local_file: config_{{ inventory_hostname }}_{{ ansible_date_time.date | replace('-','_') }}.cfg
'''

RETURN = '''
local_file:
    description: The local file path of the saved running config.
    returned: success
    type: string
    sample: '/path/to/config.cfg'
remote_file:
    description: The remote file name of the saved running config.
    returned: success
    type: string
    sample: 'config_backup.cfg'
remote_save_successful:
    description: Whether the remote save was successful.
        May be false if a remote save was unsuccessful because a file with same name already exists.
    returned: success
    type: bool
    sample: true
'''

try:
    HAS_PYNTC = True
    from pyntc import ntc_device
except ImportError:
    HAS_PYNTC = False

PLATFORM_NXAPI = 'cisco_nxos_nxapi'
PLATFORM_IOS = 'cisco_ios'
PLATFORM_EAPI = 'arista_eos_eapi'

platform_to_device_type = {
    PLATFORM_EAPI: 'eos',
    PLATFORM_NXAPI: 'nxos',
    PLATFORM_IOS: 'ios',
}

def main():
    module = AnsibleModule(
        argument_spec=dict(
            platform=dict(choices=[PLATFORM_NXAPI, PLATFORM_IOS, PLATFORM_EAPI],
                        required=True),
            remote_file=dict(required=False),
            local_file=dict(required=False),
            append_timestamp=dict(required=False),
            host=dict(required=True),
            username=dict(required=True),
            password=dict(required=True),
            secret=dict(required=False),
            transport=dict(required=False, choices=['http', 'https']),
            port=dict(required=False, type='int')
        ),
        supports_check_mode=False
    )

    if not HAS_PYNTC:
        module.fail_json(msg='pyntc Python library not found.')

    platform = module.params['platform']
    host = module.params['host']
    username = module.params['username']
    password = module.params['password']

    transport = module.params['transport']
    port = module.params['port']
    secret = module.params['secret']

    remote_file = module.params['remote_file']
    local_file = module.params['local_file']

    kwargs = {}
    if transport is not None:
        kwargs['transport'] = transport
    if port is not None:
        kwargs['port'] = port
    if secret is not None:
        kwargs['secret'] = secret

    device_type = platform_to_device_type[platform]
    device = ntc_device(device_type, host, username, password, **kwargs)

    device.open()

    if remote_file:
        remote_save_successful = device.save(remote_file)
    else:
        remote_save_successful = device.save()

    changed = remote_save_successful
    if local_file:
        device.backup_running_config(local_file)
        changed = True

    device.close()

    remote_file = remote_file or '(Startup Config)'
    module.exit_json(changed=changed, remote_save_successful=remote_save_successful, remote_file=remote_file, local_file=local_file)

from ansible.module_utils.basic import *
main()