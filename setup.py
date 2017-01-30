from setuptools import setup

setup(
    name='gobbbbler',
    version='0.3',
    packages=['gobbbbler'],
    include_package_data=True,
    install_requires=[
        'flask', 'sqlalchemy', 'requests', 'psycopg2'
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)
