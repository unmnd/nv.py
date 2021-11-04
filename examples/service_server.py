from nv.node import Node


class OddEvenCheckServer(Node):
    def __init__(self):
        super().__init__("odd_even_check_server_node")

        # The `create_service` method creates a service server.
        # The first argument is the name of the service.
        # The second argument is the callback function that will be called when a client calls the service.
        self.srv = self.create_service("odd_even_check", self.determine_odd_even)

    def determine_odd_even(self, number: int):
        # The arguments supplied can be any number of positional or keyword
        # arguments. Just make sure the node calling the service has the same arguments!

        self.log.info(f"Request received: {number}")

        # The response can be any Python data type, and is sent using the return keyword.
        return "even" if number % 2 == 0 else "odd"


def main():
    node = OddEvenCheckServer()
    node.log.debug("Odd Even Check server running")
    node.spin_until_keyboard_interrupt()


if __name__ == "__main__":
    main()
