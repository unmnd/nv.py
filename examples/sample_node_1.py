import nv
import time
import random
import numpy as np

data = b"".join(
    [
        random.randint(0, 255).to_bytes(1, "big")
        for _ in range(random.randint(0, 1024 * 1024 * 8))
    ]
)

print("Data generated")


class SampleNode1(nv.Node):
    def __init__(self):
        super().__init__(name="test_node_1")
        # self.create_timer(interval=1, callback=publish_on_timer, node=self)

        # self.create_subscription("test_topic", self.test_callback)

        # self.start_time = time.time()
        # self.stop_time = None
        # self.publish("test_topic", "test_message")

        # print(self.get_parameter("test_parameter"))
        # self.set_parameter("test_parameter", "EYOOYY")
        # print(self.get_parameter("test_parameter"))

        # self.set_parameters(
        #     [
        #         {"name": "test_parameter_1", "value": "test_value_1"},
        #         {"name": "test_parameter_2", "value": "test_value_2"},
        #     ]
        # )

        # print(self.get_parameter("test_parameter_1"))
        # print(self.get_parameter("test_parameter_2"))

        # self.set_parameters_from_file("config.yml")
        # self.set_parameters_from_file("config.json")

        # # Generate UDP server
        # udp_server = self.create_udp_server(
        #     port=12345, callback=self.test_callback, buffer_size=1024
        # )
        # udp_server.start()
        # udp_server.wait_until_ready()

        # udp_client = self.create_udp_client(port=12345, host="localhost")
        # msg = data
        # print(f"Length of message: {len(msg)} bytes")

        # # split message into chunks of size 4096
        # chunks = [msg[i : i + 1024] for i in range(0, len(msg), 1024)]

        # self.start_time = time.time()
        # for chunk in chunks:
        #     udp_client.send(chunk)

        # self.create_service("test_service", self.test_callback)

        # self.start_time = time.time()
        # future = self.call_service(
        #     "test_service", {"rich_data": 123}, 2, something="yeet"
        # )

        # future.wait()
        # self.stop_time = time.time()
        # self.log.info(f"Time taken: {self.stop_time - self.start_time}")
        # self.log.info(f"Middle time: {self.middle_time - self.start_time}")
        # self.log.info("future complete")
        # self.log.info(future.response)

        self.log.info(f"Length of data: {len(data)}")

        # Create UDP service server
        udp_server = self.create_udp_service("test_service", self.test_callback)

        self.start_time = time.time()

        # Create UDP service client
        udp_client = self.call_udp_service(
            "test_service",
            "this is the message contents",
        )

        udp_client.wait()
        self.log.info(f"Time taken to receive: {time.time() - self.start_time}")
        self.log.info(len(udp_client.get_response()))

        # Check the response matches the original data
        assert udp_client.get_response() == data

    def test_callback(self, msg):
        # self.middle_time = time.time()
        # self.log.info("Service called!")
        # self.log.info(msg)
        # self.log.info(arg2)
        # self.log.info(kwargs)
        self.log.info(f"Time taken to send: {time.time() - self.start_time}")

        return data


def main():
    node = SampleNode1()
    # timer = node.create_timer(interval=1, callback=publish_on_timer, node=node)

    # print(timer)


if __name__ == "__main__":
    main()
