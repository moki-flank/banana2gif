# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="banano2gif",
    version="1.0.0",
    author="Mag1cFall",
    author_email="lk25611295@gmail.com",
    description="Turn AI 3x3 Sprite Sheet Grid into Smooth Seamless Looping Animated GIFs (Powered by HrioAPI & Nano Banana)",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Mag1cFall/banano2gif",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Pillow>=10.0.0",
    ],
    entry_points={
        "console_scripts": [
            "banano2gif=banano2gif.cli:main",
        ],
    },
)
