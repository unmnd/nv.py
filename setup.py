from setuptools import setup

setup(
    name="nv",
    version="1.2.1",
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
        "pyro5==5.12",
    ],
    python_requires=">=3.8",
)
