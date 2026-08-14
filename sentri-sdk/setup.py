from setuptools import setup, find_packages

setup(
    name="triage-logger",
    version="1.0.0",
    description="A lightweight SDK for dispatching log events to Sentri's Triage Engine",
    author="Sentri",
    packages=find_packages(),
    install_requires=[
        "aiokafka>=0.8.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
