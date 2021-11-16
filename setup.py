from setuptools import setup
from nv import version

setup(
    name="nv",
    version=version.__version__,
    description="A Python-based robot-focused framework. Emulates rclpy for ROS in many aspects, but offers improvements and alterations where needed for Navvy.",
    license="All Rights Reserved",
    url="https://navvy.ai",
    author="UNMND, Ltd.",
    author_email="callum@unmnd.com",
    packages=["nv"],
    setup_requires=[
        "numpy==1.20.3",
    ],
    install_requires=[
        "pyyaml==6.0",
        "click==8.0.3",
        "redis==3.5.3",
        "numpy==1.20.3",
        # "numba==0.54.1",
        # "scipy==1.7.2",
        "numpy-quaternion==2021.11.4.15.26.3",
    ],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["nv=nv.__main__:main"]},
)
