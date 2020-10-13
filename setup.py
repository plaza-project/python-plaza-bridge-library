from setuptools import setup

import warnings

warnings.warn("deprecated", DeprecationWarning)

setup(name='plaza_bridge',
      version='0.0.3dev2',
      description='Helper to build PrograMaker bridges, superseeded by \'programaker-bridge\'.',
      author='kenkeiras',
      author_email='kenkeiras@codigoparallevar.com',
      url='https://gitlab.com/plaza-project/bridges/python-plaza-lib',
      license='Apache License 2.0',
      packages=['plaza_bridge'],
      scripts=[],
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: OS Independent",
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Developers",
      ],
      include_package_data=True,
      install_requires=[
          'websocket_client'
      ],
      zip_safe=False)
