import pathlib

from setuptools import find_packages, setup

README = pathlib.Path("README.md").read_text()

setup(
    name="adero",
    version="0.1.1",
    python_requires=">=3.8",
    description=(
        """
        This Python project demonstrates the usage of RabbitMQ for both
        Publish-Subscribe (PubSub) and Remote Procedure Call (RPC) communication
        patterns. RabbitMQ is a popular message broker that facilitates communication
        between different parts of a distributed application.
        """
    ),
    long_description=README,
    author="Kossam Ouma",
    author_email="koss797@gmail.com",
    packages=find_packages(
        exclude=[
            "tests",
        ]
    ),
    install_requires=["pika", "ipython", "cryptography", "msgpack", "pytz"],
)
