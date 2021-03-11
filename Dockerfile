
FROM alpine:3.7
RUN apk add --no-cache python3 py3-pip

# Temporarily install files for Python C extension compiles.
RUN apk add --no-cache --virtual .build-deps python3-dev gcc musl-dev cmake make

# Copy app files.
COPY . /app/
WORKDIR /app/
RUN pip3 install --upgrade pip
RUN pip3 install .
COPY "detector.ini.dist" "/etc/detector.ini"

# Remove temporarily installed files.
RUN apk del .build-deps

ENV RESERVER_LISTEN "0.0.0.0"
ENV RESERVER_PORT 8888
ENV RTSP_URL ""
ENV VIDEO_ENABLE "false"
ENV VIDEO_PATH ""
ENV PHOTO_ENABLE "false"
ENV PHOTO_PATH ""

EXPOSE ${RESERVER_PORT}

CMD ["python3", "-m", "doorbot", \
    "-o", "doorbot.observers.reserver", "listen", ${RESERVER_LISTEN}, \
    "-o", "doorbot.observers.reserver", "port", ${RESERVER_PORT}, \
    "-o", "doorbot.cameras.rtsp", "url", ${RTSP_URL}, \
    "-o", "doorbot.capturers.video", "enable", ${VIDEO_ENABLE}, \
    "-o", "doorbot.capturers.video", "path", ${VIDEO_PATH}, \
    "-o", "doorbot.capturers.photo", "enable", ${PHOTO_ENABLE}, \
    "-o", "doorbot.capturers.photo", "path", ${PHOTO_PATH}]

