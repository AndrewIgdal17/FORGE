from importlib.metadata import version


def test_package_version():
    assert version("forge-calc") == "1.1.0"
