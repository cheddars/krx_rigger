import setuptools

setuptools.setup(
    name="krx_rigger",
    version="0.0.29",
    install_requires=[
        'requests',
        'bs4',
        'adt_cache==0.0.12'
    ],
    license='MIT',
    author="cheddars",
    author_email="nezahrish@gmail.com",
    description="krx web crawler wrapper",
    long_description=open('README.md').read(),
    url="https://github.com/cheddars/krx_rigger",
    packages=setuptools.find_packages(),
    classifiers=[
        # 패키지에 대한 태그
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
)
