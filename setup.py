import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="gerrit_tools",
    version='0.0.7',
    author="Sergey Motyrev",
    author_email="smotyrev@gmail.com",
    description="Gerrit CLI Tool",
    url="https://github.com/smotyrev/gerrit_tools",
    packages=find_packages('.'),
    package_data={'': ['LICENSE', 'README.md']},
    include_package_data=True,
    long_description=read('README.md'),
    zip_safe=False,
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Environment :: Console',
    ],
    scripts=[],
    platforms=['Any'],
    install_requires=[],
    entry_points={
        "console_scripts": [
            'gerrit_tools = gerrit_tools.main:main',
        ]
    },
)
