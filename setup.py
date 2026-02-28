from setuptools import setup, find_packages

setup(
    name="amazon-sp-api-lite",
    version="3.0.0",
    description="Lightweight Amazon Selling Partner API Python SDK",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="platoba",
    url="https://github.com/platoba/Amazon-SP-API-Python",
    packages=find_packages(include=["sp_api", "sp_api.*"]),
    python_requires=">=3.9",
    install_requires=["requests>=2.28.0"],
    extras_require={
        "dev": ["pytest>=7.0", "pytest-cov>=4.0", "ruff>=0.1.0"],
    },
    entry_points={
        "console_scripts": ["sp-api=sp_api.cli:main"],
    },
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries",
        "Topic :: Office/Business",
    ],
)
