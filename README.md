
# doorbot
![tests](https://github.com/indigoparadox/doorbot-detector/actions/workflows/tests.yaml/badge.svg)

* [Doorbot](#doorbot)
  * [Roadmap](#roadmap)
  * [Global Configuration](#global-configuration-global)
* [Modules](#modules)
  * [Cameras](#cameras)
  * [Detectors](#cameras)
  * [Capturers](#capturers)
  * [Observers](#observers)
  * [Notifiers](#notifiers)
  * [Overlays](#overlays)

Doorbot is a set of tools originally designed to make a somewhat inflexible Amcrest IP camera a little more useful.

Doorbot is designed to run on a server (e.g. a Raspberry Pi) and use OpenCV to fetch a live RTSP stream from the designated IP camera (configured through doorbot.ini). This stream can then optionally be made available via MJPEG for web view or even through JPEG snapshots sent via an MQTT server (not included, any will do).

Doorbot also includes facilities for providing an overlay e.g. from JSON data, static text, or the current time (and maybe others later). The resulting image can also be sent directly to the server's framebuffer, if it has a display.

Snapshots or video can be captured when motion is detected, and then stored locally or uploaded via FTP. As mentioned above, they can also be sent via MQTT. A simple desktop viewer is included for receiving said snapshots in real-time.

## Global Configuration \[global\]

* **graceframes** (optional, default 10)

  The number of frames to wait before stopping a capture. This can turn what might normally be many small captures due to motion into a continuous video.

# Modules

## Cameras

### Common Configuration \[doorbot.cameras.*\]

These items can be included in any camera's configuration stanza. They only affect the camera they are under.

* **enable**

  "true" if this camera should be enabled, "false" otherwise. Currently only one camera is supported.

* **reportframes** (optional, for debugging; default 60)

  Generate a debug log entry every n frames.

* **fps**

  Frequency at which frames should be grabbed from the stream.

### \[doorbot.cameras.rtsp\]

#### Configuration

* **url**

  The URL from which the RTSP stream should be streamed. e.g. rtsp://user:password@camera ip:camera port/path_to_stream

## Detectors

### Common Configuration \[doorbot.detectors.*\]

These items can be included in any detector's configuration stanza. They only affect the detector they are under.

* **enable**

  "true" if this detector should be enabled, "false" otherwise.

### \[doorbot.detectors.motion\]

* **threshold** (optional, default 127)

  Threshold for OpenCV image detection cleanup stage.

* **varthreshold** (optional, default 20)

  varThreshold for OpenCV back_sub.

* **blur** (optional, default 5)

  Blur for OpenCV image detection cleanup stage.

* **history** (optional, default 150)

  Number of images in OpenCV back_sub history.

* **minw** (optional, default 0)

  Minimum width (in pixels) of an image difference to consider motion worth notifying about.

* **minh** (optional, default 0)

  Minimum height (in pixels) of an image difference to consider motion worth notifying about.

## Capturers

### Common Configuration \[doorbot.capturers.*\]

These items can be included in any capturer's configuration stanza. They only affect the capturer they are under.

* **enable**

  "true" if this detector should be enabled, "false" otherwise.

* **path** (optional, default "/tmp")

  The path at which to store captures. This can be a local filesystem path, or a URL to a location on an FTP server (e.g. ftp://username:password@ftp server:port/remote path). If the path starts with ftps://, then FTP over TLS will be used.

* **backuppath** (optional)

  A local filesystem path at which to store captures if they fail to upload to the given FTP server above. *If no backup path is set, captures may be lost.*

* **tsformat** (optional, default "%Y-%m-%d-%H-%M-%S-%f")

  Timestamp format to use for capture filenames.

### \[doorbot.capturers.video\]

This capturer captures activity events into video files.

#### Configuration

* **fps** (optional, default 15.0)

  FPS of the video created by the capture. Should match the FPS captured from the camera.

* **fourcc** (optional, default "mp4v")

  FourCC of the codec to use for captured video compression.

* **container** (optional, default "mp4")

  Container file extension to use for captured video files.

* **maxframes** (optional, default 100)

  Number of frames on which video files should be split. This prevents memory consumption from becoming too high at the expense of more numerous video capture files.

### \[doorbot.capturers.photo\]

This capturer captures activity events into discreet JPEG image files.

#### Configuration

There are no specific configuration options for this capturer.

## Observers

### Common Configuration \[doorbot.observers.*\]

These items can be included in any observer's configuration stanza. They only affect the observer they are under.

* **enable**

  "true" if this observer should be enabled, "false" otherwise.

* **reportframes** (optional, for debugging; default 60)

  Generate a debug log entry every n frames.

* **fps**

  Frequency at which frames should be grabbed from the stream.

Observer sections may also contain [Common Overlay Configuration Options](#common-overlay-configuration-options) in their own configuration stanzas in order to stamp an overlay on the observed image.

### \[doorbot.observers.framebuffer\]

The Framebuffer observer sends received images to the Linux framebuffer. This relieves the need for an X server on a resource-limited console.

#### Configuration

* **path**

  The filesystem path to the framebuffer device.

* **width**

  Should be set to the pixel width of the framebuffer device.

* **height**

  Should be set to the pixel height of the framebuffer device.

### \[doorbot.observers.reserver\]

The Reserver observer re-serves captured frames over HTTP, either as still JPEG images or MJPEG images. The filename requested by the server does not matter, except for the extension. Filenames ending in .jpg will return still frames, which filenames ending in .mjpeg will return MJPEG streams.

#### Configuration

* **listen**

  The interface address on which Reserver will listen for HTTP requests.

* **port**
  
  The TCP port on which Reserver will listen for HTTP requests.

## Notifiers

Notifier sections may also contain [Common Overlay Configuration Options](#common-overlay-configuration-options) in their own configuration stanzas in order to stamp an overlay on the image sent with the notification.

### Common Configuration \[doorbot.notifiers.*\]

These items can be included in any notifier's configuration stanza. They only affect the notifier they are under.

* **enable**

  "true" if this notifier should be enabled, "false" otherwise.

### \[doorbot.notifiers.mqtt\]

* **host**

  The address or hostname of the MQTT server.

* **port**

  The port on which to connect to the MQTT server.

* **uid**

  UID to use when connecting to the MQTT server. This should be unique on your MQTT server.

* **topic**

  Topic to publish activity notifications to.

* **ssl** (optional, default "false")

  "true" if TLS should be used to connect to the MQTT server, "false" otherwise.

* **ca**

  If SSL/TLS is enabled, this should contain a filesystem path to a root certificate with which to validate the server's certificate.

* **snapshots** (optional, default "false")

  If true, JPEG snapshots will accompany detection notifications at the topic "/snapshot/**topic**", where **topic** is the topic set in this configuration stanza.

* **snapsize**

  If snapshots are enabled, this should be a tuple indicating resolution to scale snapshots sent with notifications (e.g. 320,240).

* **snapsretain** (optional, default "false")

  If snapshots are enabled, this should be set to "true" to enable the retain flag on snapshot notifications, so that the last snapshot received by the server is retained and sent to newly connected subscribers until it's overwritten by the next received snapshot.

* **logger** (optional, default "false")

  For debugging purposes. "true" if extended logging should be enabled for the MQTT notifier, otherwise "false".

* **winautohide** (optional, default "false")

  For the peephole windowed client. If set to "true", the window will automatically hide on inactivity.

* **winautohidedelay**

  For the peephole windowed client. If winautohide is enabled, this should be set to the number of milliseconds (1000ths of a second) of inactivity after which the window will hide itself.

## Overlays

Overlays are 

### Common Overlay Configuration Options

These configuration options may be included In the configuration stanzas of [Observers](#observers) and [Notifiers](#notifiers) in order to stamp an overlay on the images passed to those modules.

* **overlay** (optional)

  Overlay line to be stamped on observed images. (e.g. \<weather\>\n\<time\>) Uses tokens populated by enabled overlays defined [below](#overlays).

* **overlaycoords** (optional, default 10, 10)

  Coordinates on the observer image to stamp the text overlay.

* **overlaylineheight** (optional, default 10)

  Height (in pixels) of text lines in the text overlay.

* **overlayfont** (optional, default "HERSHEY_SIMPLEX")

  Name of the (OpenCV) font to use for drawing the text overlay.

* **overlayscale** (optional, default 0.5)

  Scale at which to draw the text overlay.

* **overlaythickness** (optional, default 1)

  Thickness of the drawn font of the text overlay.

* **overlaycolor** (optional, default 255,255,255)

  Color (as an RGB integer triplet of 0-255) in which the text overlay is drawn.

### Common Configuration \[doorbot.overlays.*\]

These items can be included in any overlay's configuration stanza. They only affect the overlay they are under.

* **enable**
 
  "true" if this overlay should be enabled, "false" otherwise. **Overlays that are not enabled will not replace their designated \<tokens\>.**

### \[doorbot.overlays.weather\]

This overlay will replace the token \<weather\> in text overlays with downloaded weather data.

#### Configuration

* **url**

  URL from which to fetch the weather data JSON file.

* **refresh**
  
  Number of seconds to countdown in between fetching updated copies of the weather data JSON file.

* **format**
  
  A line indicating how to format received JSON. e.g. \<outTemp\> \<humidity\> will take from JSON elements "outTemp" and "humidity" containing "60F" and "70%" respectively to generate a line "60F 70%" which will replace the \<weather\> token in overlays.

### \[doorbot.overlays.timestamp\]

This overlay will replace the token \<time\> in text overlays with the current time.

### \[doorbot.overlays.motion\]

This overlay works in tandem with the active detectors, highlighting the activity that caused the event with a colored rectangle.
