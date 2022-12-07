# nv Framework Docs

### Welcome to the documentation for **nv (pronounced _envy_)**, a new robotics framework designed to make robot development easier, and more accessible than ever before.

![nv header image](branding/header.jpg)

> Looking for the nv website? [Click here](https://unmnd.github.io/nv-framework/nv%20Framework%20Promotional%20Document.pdf)
>
> Looking for the Python version of nv? [Click here](https://github.com/unmnd/nv.py)
>
> Looking for the JavaScipt version of nv? [Click here](https://github.com/unmnd/nv.js)

**nv** is built on two core concepts:

1. Simplicity - completing tasks and reaching development milestones should be as easy as possible for the developer, without unecessary boilerplate, configuration and setup processes, or additional dependencies that might not be used.
2. Flexibility - anything a developer wants to do should be possible with minimal additional work or implementation procedures.

While a lot of the concepts and interfaces within **nv** are similar to another
popular robot framework, ROS (Robot Operating System), there are numerous
changes and tweaks which make **nv** a more suitable framework for many developers.

# Licensing

**nv** has been published on GitHub under GPL-3.0-or-later, however you way wish
to use nv in a way which is not compatible with this license, such as within a
distributed closed-source project.

If this is the case, please contact us at <ed@unmnd.com> with your requirements for alternative licensing options.

# Quickstart

### Install using a package manager

```bash
$ pip install nv-framework
$ npm install nv-framework
```

### Run the official Docker container

```bash
$ docker run -it ghcr.io/unmnd/nv.py
$ docker run -it ghcr.io/unmnd/nv.js
```

# Introduction to nv

[🌐 1. Overview of an **nv network**](docs/intro_1_overview_of_an_nv_network.md)

[💬 2. Communicating within an nv network](docs/intro_2_communicating_within_an_nv_network.md)

[🗃️ 3. Getting and setting parameters](docs/intro_3_getting_and_setting_parameters.md)

[📐 4. Installing the nv framework](docs/intro_4_installing_the_nv_framework.md)

[⌨️ 5. nvcli - Command line tools](docs/intro_5_nvcli_command_line_tools.md)

# Tutorials

[🌱 Writing your first node (Python)](docs/tutorial_1_writing_your_first_node_python.md)

[🌱 Writing your first node (JavaScript)](docs/tutorial_1_writing_your_first_node_javascript.md)
