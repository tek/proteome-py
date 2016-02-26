from setuptools import setup, find_packages  # type: ignore

setup(
    name='proteome',
    description='project management for neovim',
    version='5.1.3',
    author='Torsten Schmits',
    author_email='torstenschmits@gmail.com',
    license='MIT',
    url='https://github.com/tek/proteome',
    packages=find_packages(
        exclude=['unit', 'unit.*', 'integration', 'integration.*']),
    install_requires=[
        'tryp-nvim>=5.1.2',
        'pygit2',
    ]
)
