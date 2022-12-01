"""Simple import and function call test"""


def test_setupcall():
    """
    Test the call of the setup function
    """
    import jupyter_code_server_proxy as jm

    print("Running test_setupcall...")
    print(jm.setup_code_server())
