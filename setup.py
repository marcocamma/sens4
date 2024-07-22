"""Python setup.py for sens4 package"""
import io
import os
from setuptools import find_packages, setup


def read(*paths, **kwargs):
    """Read the contents of a text file safely.
    >>> read("sens4", "VERSION")
    '0.1.0'
    >>> read("README.md")
    ...
    """

    content = ""
    with io.open(
        os.path.join(os.path.dirname(__file__), *paths),
        encoding=kwargs.get("encoding", "utf8"),
    ) as open_file:
        content = open_file.read().strip()
    return content


def read_requirements(path):
    return [
        line.strip()
        for line in read(path).split("\n")
        if not line.startswith(('"', "#", "-", "git+"))
    ]


setup(
    name="sens4",
    version=read("sens4", "VERSION"),
    description="sens4 created by marco cammarata",
    url="https://github.com/marcocamma/sens4/",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="marcocamma",
    packages=find_packages(where="."),
    package_dir={"": "."},
    install_requires=read_requirements("requirements.txt"),
)
