from importlib.metadata import version


def test_package_version():
    assert version("forge-calc") == "4.0.0"
