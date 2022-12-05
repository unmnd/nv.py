# 4. Installing the nv framework

Installing the nv framework is simple, as it is distributed as a single module and is available on the Python Package Index or npm Registry for Python and Node.js editions respectively.

```bash
pip install nv.py
npm install nv.js
```

Installing the module will automatically install any required dependencies. You can install globally or within a virtual environment.

<aside>
💡 **nv**cli, the command line interface for an nv network, is available with the Python version of nv. If you want to use it, install nv with pip and ensure the corresponding environment is sourced.
</aside>

# Redis

The only other requirement for an nv network is a Redis server. This can be installed following the instructions at [https://redis.io/docs/getting-started/](https://redis.io/docs/getting-started/), or by using the official docker image at [https://hub.docker.com/\_/redis](https://hub.docker.com/_/redis).

Make sure the Redis server is running and accessible when you try to launch an nv node. The node will automatically try to connect on the `localhost`, `127.0.0.1`, and `redis` domains, on port `6379`. You can override this by providing connection settings as kwargs during node initialisation, or by setting the environment variables `NV_REDIS_HOST` and `NV_REDIS_PORT`.

You can alternatively specify a unix socket for Redis communication at initialisation or using the environment variable `NV_REDIS_UNIX_SOCKET`.

# Testing the installation

Once **nv** is installed, Redis is running and accessible, and the correct environment is sourced, test the network by running `nv topic list`. As no nodes are present, the function should return an empty object `{}`. Any errors will indicate an issue with the setup.

# Next up

[5. nvcli - Command line tools](./intro_5_nvcli_command_line_tools.md)
