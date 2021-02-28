# doorbot
Doorbot is a set of tools originally designed to make a somewhat inflexible Amcrest IP camera a little more useful.

Doorbot is designed to run on a server (e.g. a Raspberry Pi) and use OpenCV to fetch a live RTSP stream from the designated IP camera (configured through doorbot.ini). This stream can then optionally be made available via MJPEG for web view or even through JPEG snapshots sent via an MQTT server (not included, any will do).

Doorbot also includes facilities for providing an overlay e.g. from JSON data, static text, or the current time (and maybe others later). The resulting image can also be sent directly to the server's framebuffer, if it has a display.

Snapshots or video can be captured when motion is detected, and then stored locally or uploaded via FTP. As mentioned above, they can also be sent via MQTT. A simple desktop viewer is included for receiving said snapshots in real-time.

## Roadmap

* Needs a bit more refactoring and unit testing.
* TensorFlow-based object detection and notification.
* Needs a proper setup package and standard layout.
* Working on a "tuner" to possibly discover better params for motion detection.

