from setuptools import setup

setup(name='programaker_bridge',
      version='0.0.4dev1',
      description='Helper to build PrograMaker bridges.',
      author='kenkeiras',
      author_email='kenkeiras@codigoparallevar.com',
      url='https://gitlab.com/programaker-project/bridges/programaker-python-lib',
      license='Apache License 2.0',
      packages=['programaker_bridge'],
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
