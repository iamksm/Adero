from setuptools import find_packages, setup

with open("README.md") as readme:
    README = readme.read()

setup(
    name="messaging_utility",
    version="0.0.1",  # noqa
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
    install_requires=[
        "pika",
        "ipython",
    ],
)
