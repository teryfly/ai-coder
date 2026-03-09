"""Setup configuration for codeAiExecutorLib."""

import os
from setuptools import setup, find_packages

# Read README.md with UTF-8 encoding to avoid UnicodeDecodeError on Windows (GBK locale)
long_description = ""
if os.path.exists("README.md"):
    with open("README.md", "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="codeAiExecutorLib",
    version="2.1.0",
    description="AI-driven batch file, folder, and shell operations with streaming feedback",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="CodeExecutor Contributors",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)