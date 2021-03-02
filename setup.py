import setuptools

setuptools.setup(
    name="programaker_bridge",
    version="0.0.4.dev7",
    description="Helper to build PrograMaker bridges.",
    author="kenkeiras",
    author_email="kenkeiras@codigoparallevar.com",
    url="https://gitlab.com/programaker-project/bridges/programaker-python-lib",
    license="Apache License 2.0",
    packages=setuptools.find_packages(),
    scripts=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
    ],
    include_package_data=False,
    install_requires=["websocket_client"],
    extras_require={
        "storage": ["sqlalchemy"],
        "full": ["sqlalchemy"],
    },
    zip_safe=True,
)
