from setuptools import setup, find_packages

version_parts = (10, 0, 3)
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
        'ribosome>=10.9.4',
        'dulwich',
    ]
)
