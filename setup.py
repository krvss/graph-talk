from os.path import join, dirname
from setuptools import setup


version = __import__('gt').__version__

LONG_DESCRIPTION = """
Graph-talk is a library for structured data processing to solve tasks like parsing,
interpreting, or converting in a simple and comprehensible for humans manner.

Library uses 3 key concepts to achieve the goal: use graph-like representation of
information and its processing; dialog-like communication between the model and
the process; handler-event approach to recognize the input messages.
"""


def long_description():
    """Return long description from README.rst if it's present
    because it doesn't get installed."""
    try:
        return open(join(dirname(__file__), 'README.rst')).read()
    except IOError:
        return LONG_DESCRIPTION


setup(
    name='graph-talk',
    version=version,
    packages=['gt'],
    url='https://github.com/krvss/graph-talk/',
    license='Apache Software License',
    author='Stas Kravets',
    author_email='stas.kravets@gmail.com',
    description='Library for structured information processing: parsing, interpreting, converting, etc.',
    include_package_data=True,
    platforms='any',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: General',
    ]
)
