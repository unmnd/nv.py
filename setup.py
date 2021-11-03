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
    install_requires=[
        "pyyaml==6.0",
        "click==8.0.3",
        "redis==3.5.3",
        "serpent==1.40",
    ],
    python_requires=">=3.8",
)
