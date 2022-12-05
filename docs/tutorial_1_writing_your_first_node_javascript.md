# Writing your first node (JavaScript)

Wow, now you have a good overview of what the **nv** network is, and how it’s supposed to work, it’s about time to start writing your own nodes!

Ensure the Redis server is running and accessible, launch your favourite text editor or IDE, and create a new file called `myFirstNode.js`.

Every node is built off the `Node` class, which can be imported from the `nv` package.

```jsx
const { Node } = require("nv");
```

This `Node` class is used as the base to build the rest of your node. We will be focussing on an object-oriented approach to programming from this point on, however the class can be used in a more functional approach as well.

Inherit the `Node` class into our own class, `HelloWorldNode`, and add an initialisation method. The `init` method is already used by the parent `Node` class to perform important initialisation steps, so it’s vital to call that parent method. It’s best to do that before any other initialisation code.

```jsx
class HelloWorldNode extends Node {
    async init() {
        await super.init();
```

This initialisation function is a good place to put any one-time run code, such as creation of global variables, spawning of timers, serial connections to hardware, etc.

Let’s add a class variable called `currentEmotion`, which we will initialise to an empty string and will be updated later. Let’s also create a subscription to the topic `internal_thoughts`. The callback function supplied is the function that’s called when a new message is received.

Finally let’s call the function `publishEmotions`, which we will write later.

```jsx
        this.currentEmotion = "";
        this.createSubscription(
            "internal_thoughts",
            this.processThoughts.bind(this)
        );
        this.publishEmotions();
    }
```

Let’s create that callback function now. The message received is the first positional argument. In this case, the message received should be a string, so we can log a warning if it’s not. The class’ `log` method allows different error levels and provides consistent formatting for log messages.

```jsx
    processThoughts(msg) {
        // Ensure the message is a string
        if (typeof msg !== "string") {
            this.log.warning("Received non-string message");
            return;
        }
```

Let’s search the message received for any emotion text, and update the current emotion variable if we find anything.

```jsx
        // Search the message for an emotion
        if (msg.includes("happy")) {
            this.currentEmotion = "happy";
        } else if (msg.includes("sad")) {
            this.currentEmotion = "sad";
        } else if (msg.includes("angry")) {
            this.currentEmotion = "angry";
        }
    }
```

As we know, robot brains are only capable of feeling these three basic emotions, so we’ve covered all the bases here. I’ll leave you to improve the implementation of emotion checking if you feel like a challenge.

Let’s write the other function, `publishEmotions`. The important lines are the `publish` method, which allows publishing of data onto the **nv** network, and the line which monitors the `stopped` event or variable, used to ensure any loops exit when the node is terminated.

```jsx
    publishEmotions() {
        if (!this.stopped) {
            this.publish("emotions", this.currentEmotion);
            setTimeout(() => {
                this.publishEmotions();
            }, 1000);
        }
    }
```

We now have everything we need for our new `HelloWorldNode` class. To keep it’s simple, the next lines just create and initialise the node.

```jsx
const node = new HelloWorldNode({ nodeName: "my_first_node" });
node.init();
```

<aside>
🚨 Define the name of the node by passing it inside an object to the class constructor.

</aside>

All together, your node should look like this:

```jsx
const { Node } = require("nv");

class HelloWorldNode extends Node {
    async init() {
        await super.init();

        this.currentEmotion = "";
        this.createSubscription(
            "internal_thoughts",
            this.processThoughts.bind(this)
        );
        this.publishEmotions();
    }

    processThoughts(msg) {
        // Ensure the message is a string
        if (typeof msg !== "string") {
            this.log.warning("Received non-string message");
            return;
        }

        // Search the message for an emotion
        if (msg.includes("happy")) {
            this.currentEmotion = "happy";
        } else if (msg.includes("sad")) {
            this.currentEmotion = "sad";
        } else if (msg.includes("angry")) {
            this.currentEmotion = "angry";
        }
    }

    publishEmotions() {
        if (!this.stopped) {
            this.publish("emotions", this.currentEmotion);
            setTimeout(() => {
                this.publishEmotions();
            }, 1000);
        }
    }
}

const node = new HelloWorldNode({ nodeName: "my_first_node" });
node.init();
```

Launching the node should display some debug information, finishing with a successful registration message. Terminate the node by sending a SIGINT command, typically by pressing `Ctrl+c`.

![tutorial_run_js.gif](img/tutorial_1_run_js.gif)

To test it’s working, let’s open two new terminals. In the first one, use **nv**cli to echo the output of the `emotions` topic. In the second, experiment with publishing data to the `internal_thoughts` topic.

![tutorial_final.gif](img/tutorial_1_final.gif)

# Improvements to the node

Although the node written is perfectly functional, there are some improvements which we can make. One issue with our implementation is that upon receiving a termination signal the loop will continue waiting (from `setTimeout`) for up to a whole loop duration. This doesn’t matter much here where the loop duration is 1 second, but with loops of minutes or hours, this could cause major issues.

We can use the `timeouts` array provided to the class to automatically cancel any timeouts when the node is destroyed. We just need to add any timeouts we create to this array, and the node will stop them when the node is destroyed.

```jsx
this.timeouts["publish_emotions"] = setTimeout(() => {
    this.publishEmotions();
}, 1000);
```
