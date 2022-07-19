# -*- coding: utf-8 -*-
import fastentrypoints  # lgtm [py/unused-import]
import codecs
import subprocess

from setuptools import setup, find_packages
from ocrd_browser import __version__

install_requires = open('requirements.txt').read().split('\n')

print("Generating gresource bundle")
subprocess.call(
    [
        "glib-compile-resources",
        "--sourcedir=gresources",
        "--target=ocrd_browser/ui.gresource",
        "gresources/ocrd-browser.gresource.xml",
    ]
)

setup(
    name='browse-ocrd',
    version=__version__,
    author='Johannes Künsebeck',
    author_email='kuensebeck@googlemail.com',
    description='An extensible viewer for OCR-D workspaces',
    license='MIT License',
    long_description=codecs.open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/hnesk/browse-ocrd",
    packages=find_packages(exclude=('tests', 'repo', 'venv', 'build')),
    python_requires=">=3.7",
    install_requires=install_requires,
    include_package_data=True,
    setup_requires=['wheel'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: MIT License',
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Image Recognition'
    ],
    keywords=['OCR', 'OCR-D', 'mets', 'PAGE Xml'],
    entry_points={
        'console_scripts': [
            'browse-ocrd = ocrd_browser.main:main',
        ],
        'ocrd_browser_view': [
            'xml = ocrd_browser.view:ViewXml',
            'html = ocrd_browser.view:ViewHtml',
            'text = ocrd_browser.view:ViewText',
            'images = ocrd_browser.view:ViewImages',
            'diff = ocrd_browser.view:ViewDiff',
            'page = ocrd_browser.view:ViewPage'
        ],

    },
    package_data={
        '' : ['*.gresource','*.ui', '*.xml']
    },
)
