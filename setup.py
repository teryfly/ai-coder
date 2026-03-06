"""Setup configuration for codeAiExecutorLib."""

from setuptools import setup, find_packages

setup(
    name="codeAiExecutorLib",
    version="2.0.0",
    description="AI-driven batch file, folder, and shell operations with streaming feedback",
    long_description=open("README.md").read() if open("README.md") else "",
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