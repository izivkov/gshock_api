from setuptools import setup, find_packages

setup(
    name='gshock_api',
    version='2.0.27',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=[
        'pytz',
        'bleak>=1.0.1',
    ],
    entry_points={
        'console_scripts': [
            'gshock_server=examples.gshock_server:main',
        ],
    },
)
