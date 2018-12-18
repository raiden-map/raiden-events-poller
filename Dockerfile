FROM python:3.7.1-alpine3.8 as builder
ENV PYTHONUNBUFFERED 1

RUN apk add --no-cache --upgrade \
        alpine-sdk \
        libtool \
        libffi-dev \
        gmp-dev ; \
#
    apk add --no-cache \
            --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
        openssl ; \
# librdkafka must be installed from community edge channel.
    apk add --no-cache \
            --repository http://dl-cdn.alpinelinux.org/alpine/edge/community \
        librdkafka \
        librdkafka-dev

WORKDIR /wheels

COPY requirements.txt .

RUN pip3 wheel -r requirements.txt

FROM python:3.7.1-alpine3.8 AS runner
ENV PYTHONUNBUFFERED 1

COPY --from=builder /wheels /wheels


RUN pip3 install -r /wheels/requirements.txt \
                -f /wheels ; \
    rm -rf /wheels ; \
    rm -rf /root/.cache/pip/* ; \
#
    apk add --no-cache --upgrade \
        alpine-sdk \
        libtool \
        libffi-dev \
        gmp-dev ; \
#
    apk add --no-cache \
            --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
        openssl ; \
#
    apk add --no-cache \
            --repository http://dl-cdn.alpinelinux.org/alpine/edge/community \
        librdkafka \
        librdkafka-dev ; 

WORKDIR /app
    
COPY ./raiden-events-poller /app 
COPY ./event-schemas /app/event-schemas

CMD [ "python3", "raiden_poller_cli.py" ]

LABEL maintainer.name="Raiden Map Team"
LABEL maintainer.email="info@raidenmap.io"