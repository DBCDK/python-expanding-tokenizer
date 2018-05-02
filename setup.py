from setuptools import find_packages, setup

setup(
    name='expanding-tokenizer',
    version='0.9',
    packages=['expanding'],
    package_dir={'expanding': 'expanding'},
    options={
        'build_exe': {
            'packages': find_packages(exclude=['tests', 'example'])
        }
    },
    url='https://github.com/kosmisk-dk/python-expanding-tokenizer',
    license='gpl3',
    author='kosmisk-dk',
    author_email='source@kosmisk.dk',
    description="Variable expanding tokenizer",
    long_description="""Designed for easy parsing of files.
Produces an interface that allows for pattern matching of input on a
TokenType basis."""
)
