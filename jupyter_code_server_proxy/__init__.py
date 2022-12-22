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
import re
import time
import stat
import logging
import json
from pathlib import Path
import secrets

from typing import Any
from typing import Dict

import tornado


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
    # Get code server env root directory if set
    code_server_env_root = os.environ.get('CODE_SERVER_ENV_ROOT', '')
    # Update code_server_executable
    if code_server_env_root:
        code_server_executable = os.path.join(
            code_server_env_root, 'bin', code_server_executable
        )

    # generate file with random one-time-password
    code_server_passwd = str(secrets.token_hex(16))

    # Get home dir
    home_dir = os.path.expanduser('~')

    # code-server specific dirs
    user_dir = os.path.join(os.environ.get(
        'WORK', default=home_dir), 'code-server'
    )
    extensions_dir = os.path.join(os.environ.get(
        'WORK', default=home_dir), 'code-server', 'extensions'
    )

    # Config file name
    # Each lab instance can have its own config file. We do not want to overwrite
    # existing lab config. So we prepend name of config with lab server name
    code_server_config_file_name = os.environ.get(
        'JUPYTERHUB_SERVER_NAME', default='jupyterlab'
    )
    code_server_config_file = os.path.join(
        home_dir, '.config', 'code-server',
        f'{code_server_config_file_name}-config.yaml'
    )

    def forbid_port_forwarding(response, request):
        """Forbid the port forwarding requests to code server"""
        if re.search(f'(.*)/code_server_[0-9]/proxy/([0-9]*)', request.uri):
            response.code = 403
            raise tornado.web.HTTPError(
                403, 'Port forwarding using code server is forbidden!!'
            )

    # Write code server config file to user's home
    def _write_config_file():
        """Write config file to config directory"""
        # code-server config dir
        code_server_config_dir = os.path.dirname(code_server_config_file)
        # Ensure config dir exists
        os.makedirs(code_server_config_dir, exist_ok=True)
        try:
            # Check last modifed time of config file
            last_modified = os.path.getmtime(code_server_config_file)
            # If last modified is less than 7 days, do not update password
            if time.time() - last_modified < 604800:
                return
        except FileNotFoundError:
            # If file does not exist continue
            pass
        # Config file attributes
        config = {
            'auth': 'password',
            'password': code_server_passwd,
            'cert': False,
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
        if not os.path.exists(code_server_executable):
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

export PATH={code_server_env_bin}:$PATH

# We need to send this process to background or else bash
# will ignore TERM signal as it will wait for code-server to finish
# before taking signal into account
{code_server_executable} "$@" &
wait
""".format(
    code_server_executable=code_server_executable,
    code_server_env_bin=os.path.join(code_server_env_root, 'bin')
)

        # Fall back root directory. By default we use JOBSCRATCH to place ephermal
        # scripts. If this is not available we need to have a smart fallback
        # option to take different users and different JupyterLab instances
        # into account.
        # Fallback to fallback is /tmp/$USER
        fallback_scratch_dir_prefix = os.environ.get(
            'JUPYTER_CONFIG_DIR', default=os.path.join(
                '/tmp', os.environ.get('USER')
            )
        )
        # Root directory to save the code server wrapper
        scratch_dir_perfix = os.environ.get(
            'JOBSCRATCH', default=fallback_scratch_dir_prefix
        )
        scratch_dir = os.path.join(
            scratch_dir_perfix,
            'bin',
            os.environ.get('JUPYTERHUB_SERVER_NAME', default='jupyterlab')
        )
        # Check if scratch dir exists and create one if it does not
        if not os.path.exists(scratch_dir):
            os.makedirs(scratch_dir, exist_ok=True)
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
        # NOTE: seems like extensions-dir in config file is ignored. Maybe
        # we should put an issue in the upstream project?
        # We pass the extensions-dir argument as CLI
        cmd_args = [
            code_server_wrapper, '--bind-addr', f'127.0.0.1:{port}',
            '--config', code_server_config_file, '--user-data-dir', user_dir,
            '--extensions-dir', extensions_dir, '--disable-telemetry',
            '--disable-update-check'
        ]

        # If arguments like host, port are found in config, delete them.
        # We let Jupyter server proxy to take care of them
        # Additionally we delete path_prefix as well.
        for arg in [
            '--bind-addr', '--install-extension',
            '--extensions-dir', '--user-data-dir'
            ]:
            if arg in args:
                idx = args.index(arg)
                del args[idx:idx + 2]

        _write_config_file()
        logger.info(
            'Code server config file is written at %s', code_server_config_file
        )

        # Append user provided arguments to cmd_args
        cmd_args += args

        logger.info(
            'Code server will be launched with arguments %s', cmd_args
        )

        return cmd_args

    return {
        'command': _code_server_command,
        'absolute_url': False,
        'timeout': 300,
        'new_browser_tab': True,
        'rewrite_response': forbid_port_forwarding,
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
