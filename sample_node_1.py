import nv
import time


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

        # Generate UDP server
        udp_server = self.create_udp_server(
            port=12345, callback=self.test_callback, buffer_size=1024
        )
        udp_server.start()
        udp_server.wait_until_ready()

        udp_client = self.create_udp_client(port=12345, host="localhost")
        msg = "test_message".encode()
        self.start_time = time.time()
        udp_client.send(msg)

    def test_callback(self, msg):
        self.stop_time = time.time()
        self.log.warning(msg)
        self.log.warning(f"Time elapsed: {self.stop_time - self.start_time}")

        self.log.warning("test_callback: {}".format(msg))


def main():
    node = SampleNode1()
    # timer = node.create_timer(interval=1, callback=publish_on_timer, node=node)

    # print(timer)


if __name__ == "__main__":
    main()
