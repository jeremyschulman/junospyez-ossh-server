from setuptools import setup, find_packages

import junospyez_ossh_server.about as about


def requirements(filename='requirements.txt'):
    return open(filename.strip()).readlines()


with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name=about.package_name,
    version=about.package_version,
    description='Outbound SSH for use with Junos systems',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Jeremy Schulman',
    author_email='jschulman@juniper.net',
    packages=find_packages(),
    install_requires=requirements(),
    url='https://github.com/jeremyschulman/junospyez-ossh-server',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
