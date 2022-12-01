# jupyter-code-server-proxy
Integrate Code server in the Jupyter environment.

## Requirements
- Python 3.6+
- Jupyter Notebook 6.0+
- JupyterLab 2.1+

This package executes the `code-server` command. This command assumes the `code-server` command is available in the environment's.

## Jupyter-Server-Proxy
[Jupyter-Server-Proxy](https://jupyter-server-proxy.readthedocs.io) lets you run arbitrary external processes (such as MLflow) alongside your notebook, and provide authenticated web access to them.

## Install

#### Create and Activate Environment
```
virtualenv -p python3 venv
source venv/bin/activate
```

#### Install jupyter-mlflow-proxy
```
pip install git+https://gitlab.com/idris-cnrs/jupyter/jupyter-proxy-apps/jupyter-code-server-proxy.git
```

#### Enable jupyter-server-proxy Extensions

For Jupyter Lab, install the @jupyterlab/server-proxy extension:
```
jupyter labextension install @jupyterlab/server-proxy
```
