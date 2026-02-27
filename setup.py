from setuptools import setup

setup(
    name="amazon-sp-api-lite",
    version="1.0.0",
    description="Lightweight Amazon Selling Partner API Python SDK",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="platoba",
    url="https://github.com/platoba/Amazon-SP-API-Python",
    py_modules=["sp_api"],
    python_requires=">=3.8",
    install_requires=["requests>=2.28.0"],
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries",
    ],
)
