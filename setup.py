from setuptools import setup, find_packages  # type: ignore

setup(
    name='proteome',
    description='project management for neovim',
    version='0.2.3',
    author='Torsten Schmits',
    author_email='torstenschmits@gmail.com',
    license='MIT',
    url='https://github.com/tek/proteome',
    packages=find_packages(exclude=['unit', 'unit.*']),
    install_requires=[
        'tryp-nvim',
        'pyrsistent',
    ]
)
