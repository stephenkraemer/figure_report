"""Create HTML report from set of hierarchically grouped figures"""

from setuptools import find_packages, setup

setup(
    name='figure_report',
    version='0.1',
    description='Create HTML report from set of hierarchically grouped figures',
    long_description=__doc__,
    url='',
    author='Stephen Kraemer',
    author_email='stephenkraemer@gmail.com',
    license='MIT',
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    keywords='report bioinformatics data_science',

    package_dir={'': 'src'},
    packages = find_packages(where='src',
                             exclude=['docs']),
    package_data = {},
    data_files = [],

    install_requires=[],
    python_requires='>=3.6',

)
