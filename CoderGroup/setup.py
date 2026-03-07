from setuptools import setup, find_packages

setup(
    name="agentCoderGroupLib",
    version="0.1.3",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "agentcoder=agentCoderGroupLib.entry.console_runner:main",
        ]
    },
)
