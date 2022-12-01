# Copyright 2022 IDRIS / jupyter
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import stat
import time
import logging
import shutil
import json
from pathlib import Path
import secrets

from typing import Any
from typing import Dict


def get_logger(name):
    """Configure logging"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Prevent logging from propagating to the root logger
        logger.propagate = 0
        console = logging.StreamHandler()
        logger.addHandler(console)
        formatter = logging.Formatter(
            '[%(levelname).1s %(asctime)s.%(msecs)03d %(module)s '
            '%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console.setFormatter(formatter)
    return logger


def setup_code_server() -> Dict[str, Any]:
    """ Setup commands and and return a dictionary compatible
        with jupyter-server-proxy.
    """

    # Set logging
    logger = get_logger(__name__)
    logger.setLevel(logging.INFO)

    code_server_executable = 'code-server'

    # generate file with random one-time-password
    code_server_passwd = str(secrets.token_hex(16))

    # Config file name
    # Each lab instance can have its own config file. We do not want to overwrite
    # existing lab config. So we prepend name of config with lab server name
    code_server_config_file_name = os.env.get(
        'JUPYTERHUB_SERVER_NAME', default='jupyterlab'
    )
    code_server_config_file = os.path.join(
        os.path.expanduser('~'), '.config', 'code-server',
        f'{code_server_config_file_name}-config.yaml'
    )

    # Write code server config file to user's home
    def _write_config_file():
        """Write config file to config directory"""
        # Ensure config dir exists
        os.makedirs(os.path.dirname(code_server_config_file), exist_ok=True)
        # Config file attributes
        config = {
            'auth': 'password',
            'password': code_server_passwd,
            'cert': False,
            'user-data-dir': os.environ['WORK'],
        }
        # Dump config file
        with open(code_server_config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def _get_icon_path():
        """Get the icon path"""
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'icons',
            'code-server-logo.svg'
        )

    def _code_server_command(port, args):
        """Callable that we will pass to sever proxy to spin up
        code server"""
        # Check if code server executable is available
        executable = shutil.which(code_server_executable)
        if not executable:
            raise FileNotFoundError(
                f'{code_server_executable} executable not found.'
            )

        script_template = """#!/bin/bash
exit_script() {{
    get_child_pids $$
    trap - SIGTERM # clear the trap
    kill -INT $CPIDS # Sends SIGTERM to child/sub processes
    exit 0
}}

function get_child_pids() {{
    pids=`pgrep -P $1|xargs`
    for pid in $pids;
    do
        CPIDS="$CPIDS $pid"
        get_child_pids $pid
    done
}}

trap exit_script SIGTERM

CPIDS=''

# We need to send this process to background or else bash
# will ignore TERM signal as it will wait for code-server to finish
# before taking signal into account
{code_server_executable} "$@" &
wait
""".format(code_server_executable=code_server_executable)

        # Directory to save the code server wrapper
        scratch_dir = os.environ.get('JOBSCRATCH', default='/tmp')
        # Path to code server wrapper
        code_server_wrapper = os.path.join(
            scratch_dir, 'code_server_wrapper.sh'
        )
        # Write wrapper script to directory
        with open(code_server_wrapper, 'w') as f:
            f.write(script_template)
        # Make it executable
        st = os.stat(code_server_wrapper)
        os.chmod(code_server_wrapper, st.st_mode | stat.S_IEXEC)

        # Make code-server command arguments
        cmd_args = [
            code_server_wrapper, '--bind-addr', f'127.0.0.1:{port}',
            '--config', code_server_config_file,
        ]

        # If arguments like host, port are found in config, delete them.
        # We let Jupyter server proxy to take care of them
        # Additionally we delete path_prefix as well.
        for arg in ['--bind-addr', '--install-extension']:
            if arg in args:
                idx = args.index(arg)
                del args[idx:idx + 2]

        # Append user provided arguments to cmd_args
        cmd_args += args

        # Write password to a file so that user can read it
        # fpath_passwd = _write_passwd_file()
        # logger.info('Password file for Code server: %s', fpath_passwd)

        _write_config_file()
        logger.info(
            'Code server config file is written at %s', code_server_config_file
            )

        logger.info(
            'Code server will be launched with arguments %s', cmd_args
        )

        return cmd_args

    return {
        'command': _code_server_command,
        'absolute_url': False,
        'timeout': 300,
        'new_browser_tab': True,
        'launcher_entry': {
            'enabled': True,
            'title': 'Code server',
            'num_instances': 1,
            'icon_path': _get_icon_path(),
            'category': 'Applications',
        }
    }

from . import _version
__version__ = _version.get_versions()['version']
