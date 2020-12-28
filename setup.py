import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simplebt",
    version="0.0.1",
    author="arocketman",
    author_email="gipaetusb@pm.me",
    description="It's pip... with git.",
    long_description=long_description,
    url="https://github.com/gipaetusb/SimpleBacktester",
    packages=setuptools.find_packages(),
    install_requires=[
        "ib-insync==0.9.64",
        "matplotlib==3.2.1",
        "numpy==1.19.4",
        "pandas==1.0.4",
        "psycopg2-binary==2.8.5",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
