from setuptools import setup

setup(
    name="SimpleBacktester",
    version="0.1",
    description="backtester engine",
    classifiers=[
        "Programming Language :: Python :: 3.8"
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    install_requires=[
        "ib-insync",
        "matplotlib",
        "numpy",
        "pandas",
        "psycopg2"
    ],
)
