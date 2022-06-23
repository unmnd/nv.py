from setuptools import setup

setup(
    name="nv",
    version="1.24.9",
    description="A Python-based robot-focused framework.",
    license="All Rights Reserved",
    url="https://navvy.ai",
    author="UNMND, Ltd.",
    author_email="callum@unmnd.com",
    packages=["nv"],
    install_requires=[
        "pyyaml==6.0",
        "click==8.0.3",
        "redis==3.5.3",
        # "numpy==1.20.3",
        # "numpy-quaternion==2021.11.4.15.26.3",
        "orjson==3.6.8",
        "psutil==5.9.1",
    ],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["nv=nv.__main__:main"]},
)
