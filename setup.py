#!/usr/bin/env python3

from setuptools import setup

setup(
    name="cb-psc-integration",
    version="0.0.1",
    url="https://developer.carbonblack.com/",
    license="MIT",
    author="Carbon Black",
    author_email="dev-support@carbonblack.com",
    description="Carbon Black PSC Integration Library",
    long_description=__doc__,
    packages=["cb.psc.integration"],
    package_dir={"": "src"},
    platforms="any",
    classifiers=[
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[
        "cbapi == 1.5.1",
        "croniter",
        "Flask",
        "frozendict",
        "pyyaml",
        "redis",
        "requests",
        "rq == 1.1.0",
        "rq-scheduler == 0.8.3",
        "schema",
        "supervisor == 4.0.4",
        "Sphinx",
        "SQLAlchemy",
        "validators >= 0.14.0",
        "yara-python",
    ],
)
