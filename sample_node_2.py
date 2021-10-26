import nv

def main():
    node = nv.create_node(name='test_node_2')
    node.subscribe(topic='test_topic_1', callback=callback_function)


def callback_function(msg):
    print("This is a callback")
    print(msg)


if __name__ == '__main__':
    main()