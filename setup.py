import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ymp",
    version="0.92b1",
    author="pheinze",
    author_email="pheinze82@gmail.com",
    description="A command-line music player for YouTube.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pheinze/ymp",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
    install_requires=[
        'yt_dlp',
        'pyfiglet',
        'requests',
        'pydub',
        'termcolor',
        'beautifulsoup4',
        'colorama',
        'lxml',
        'simpleaudio',
        'rich',
        'setuptools',
        'textual',
    ],
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': ['ymp = ymp.__main__:main']
    },
)
