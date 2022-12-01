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


from os import path
from setuptools import setup, find_packages
import versioneer

HERE = path.abspath(path.dirname(__file__))
with open(path.join(HERE, 'README.md'), 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='jupyter-code-server-proxy',
    packages=find_packages(),

    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),

    url='https://gitlab.com/i2461/jupyter/jupyter-code-server-proxy',

    author='Mahendra Paipuri',
    author_email='mahendra.paipuri@idris.fr',

    description='Code server for JupyterLab',
    long_description=long_description,
    long_description_content_type='text/markdown',

    keywords=['jupyter', 'code-server', 'jupyterhub', 'jupyter-server-proxy'],
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Science/Research",
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache License 2.0',
        'Framework :: Jupyter',
    ],

    entry_points={
        'jupyter_serverproxy_servers': [
            'code_server = jupyter_code_server_proxy:setup_code_server',
        ]
    },
    package_data={
        'jupyter_code_server_proxy': ['icons/code-server-logo.png'],
    },
    # install_requires=['jupyter-server-proxy==3.2.1'],
    include_package_data=True,
    zip_safe=False
)
