from setuptools import setup, find_packages

setup(
    name="cohdl",
    version="0.1",
    description="A Python to VHDL compiler",
    author="Alexander Forster",
    author_email="alexander.forster123@gmail.com",
    packages=find_packages(exclude=["tests", "tests.*"]),
)
