from setuptools import setup, find_packages

from version import version

setup(
    name='proteome',
    description='project management for neovim',
    version=version,
    author='Torsten Schmits',
    author_email='torstenschmits@gmail.com',
    license='MIT',
    url='https://github.com/tek/proteome',
    packages=find_packages(
        exclude=['unit', 'unit.*', 'integration', 'integration.*']),
    install_requires=[
        'tryp-nvim>=6.3.0',
        'tryp>=6.6.0',
        'dulwich',
    ]
)
