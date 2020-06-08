"""Setup file for rhasspy_lisa_odas_hermes"""
import os

import setuptools

this_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_dir, "README.md"), "r") as readme_file:
    long_description = readme_file.read()

with open(os.path.join(this_dir, "requirements.txt"), "r") as requirements_file:
    requirements = requirements_file.read().splitlines()

with open(os.path.join(this_dir, "VERSION"), "r") as version_file:
    version = version_file.read().strip()

setuptools.setup(
    name="rhasspy-lisa-odas-hermes",
    version=version,
    author="Lawrence Iviani",
    author_email="lawrence.iviani@gmail.com",
    url="https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "rhasspy-lisa-odas-hermes = rhasspy_lisa_odas_hermes.__main__:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
)
