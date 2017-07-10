FROM python:3-alpine

RUN set -x \
    && apk --update --no-cache add make \
    && apk --update --no-cache --virtual .build-dep add \
        build-base \
    && pip install --upgrade pip \
    && pip install cython \
    && pip install --no-binary :all: falcon \
    && pip install gunicorn \
    && pip install gevent \
    && pip install boto \
    && pip install secretary \
    && apk del .build-dep

WORKDIR /usr/src/app

COPY server.py ./server.py

CMD gunicorn -b 0.0.0.0:3002 --worker-class gevent --threads 3 server:app
