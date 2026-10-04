from importlib.metadata import version


def test_package_version():
    assert version("forge-calc") == "2.0.0"
