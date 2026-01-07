from setuptools import setup, find_packages

setup(
    name="gh-perf-report",
    version="0.1.0",
    description="GitHub CI Performance Report Parser for tt-forge and tt-xla",
    author="Tenstorrent",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "gh-perf-report=gh_perf_report.cli:cli",
        ],
    },
    python_requires=">=3.8",
)
