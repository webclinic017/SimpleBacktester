import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simplebt",
    version="0.0.1",
    author="kaya",
    author_email="gipaetusb@pm.me",
    description="A simple simplebt",
    long_description=long_description,
    url="https://github.com/gipaetusb/SimpleBacktester",
    packages=setuptools.find_packages(),
    install_requires=[
        "ib-insync==0.9.64",
        "matplotlib==3.3.3",
        "numpy==1.19.4",
        "pandas==1.2.0",
        "psycopg2-binary==2.8.6",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
