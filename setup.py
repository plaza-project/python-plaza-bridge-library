from setuptools import setup

setup(name='plaza_bridge',
      version='0.0.2dev11',
      description='Helper to build plaza bridges.',
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
          "Development Status :: 1 - Planning",
          "Intended Audience :: Developers",
      ],
      include_package_data=True,
      install_requires=[
          'websocket_client'
      ],
      zip_safe=False)
