from setuptools import setup

setup(
    name="nv",
    version="1.1.0",
    description="A Python-based robot-focused framework. Emulates rclpy for ROS in many aspects, but offers improvements and alterations where needed for Navvy.",
    license="All Rights Reserved",
    url="https://navvy.ai",
    author="UNMND, Ltd.",
    author_email="callum@unmnd.com",
    packages=["nv"],
    install_requires=[
        "bidict==0.21.4",
        "certifi==2021.10.8",
        "charset-normalizer==2.0.7",
        "idna==3.3",
        "python-engineio==4.2.1",
        "python-socketio[client]==5.4.1",
        "requests==2.26.0",
        "urllib3==1.26.7",
        "pyyaml==6.0",
        "click==8.0.3",
        "redis==3.5.3",
        "serpent==1.40",
    ],
    python_requires=">=3.8",
)
