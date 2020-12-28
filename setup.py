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
        "ib-insync==0.9.64",
        "matplotlib==3.2.1",
        "numpy==1.19.4",
        "pandas==1.0.4",
        "psycopg2-binary==2.8.5"
    ],
)
