from nv.node import Node
import nv.exceptions


class OddEvenCheckClient(Node):
    def __init__(self):
        super().__init__("odd_even_check_client_node")

        self.log.debug("Odd Even Check client making a request")

        # Call any service using the `call_service` method
        # The service name is the first argument, and any number of args or
        # kwargs can be passed afterwards. Ensure the arguments match what is
        # expected by the service server!
        try:
            self.future = self.call_service("odd_even_check", number=5)
        except nv.exceptions.ServiceNotFoundException:
            self.log.error(f"Service not found: odd_even_check")
            self.destroy_node()
            exit()

        # Wait until a response has been received
        self.future.wait(timeout=5)

        # Get the response
        self.log.info(f"Result: The number was {self.future.get_response()}!")


def main():
    node = OddEvenCheckClient()

    node.spin_until_keyboard_interrupt()


if __name__ == "__main__":
    main()
