from setuptools import setup, find_packages

version_parts = (7, 5, 1)
version = '.'.join(map(str, version_parts))

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
        'tryp-nvim>=7.4.0',
        'tryp>=7.4.0',
        'dulwich',
    ]
)
