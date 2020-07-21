# -*- coding: utf-8 -*-
import codecs
import subprocess

import setuptools
from setuptools import setup
from ocrd_browser import __version__

install_requires = open('requirements.txt').read().split('\n')

print("Generating gresources bundle")
subprocess.call(
    [
        "glib-compile-resources",
        "--sourcedir=resources",
        "--target=ocrd_browser/ui.gresource",
        "resources/ocrd-browser.gresource.xml",
    ]
)

setup(
    name='browse-ocrd',
    version=__version__,
    author='Johannes Künsebeck',
    author_email='kuensebeck@googlemail.com',
    description='An extensible viewer for OCRD mets.xml files',
    license='MIT License',
    long_description=codecs.open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/hnesk/browse-ocrd",
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    include_package_data=True,
    setup_requires=['wheel'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Image Recognition'
    ],
    keywords=['OCR', 'OCRD', 'mets', 'PAGE Xml'],
    entry_points={
        'console_scripts': [
            'browse-ocrd = ocrd_browser.main:main',
        ]
    },
    package_data={'ocrd_browser': ['*.gresource']},
)
