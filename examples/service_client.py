from nv import Node
import nv.exceptions


class OddEvenCheckClient(Node):
    def __init__(self):
        super().__init__("odd_even_check_client_node")

        # You can wait for a service to be ready using the
        # `wait_for_service_ready` method.
        self.wait_for_service_ready("odd_even_check")

        self.log.debug("Odd Even Check client making a request")

        # Call any service using the `call_service` method
        # The service name is the first argument, and any number of args or
        # kwargs can be passed afterwards. Ensure the arguments match what is
        # expected by the service server!
        result = self.call_service("odd_even_check", number=5)

        # Get the response
        self.log.info(f"Result: The number was {result}!")


def main():
    node = OddEvenCheckClient()

    node.spin()


if __name__ == "__main__":
    main()
