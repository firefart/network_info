FROM python:3-alpine
MAINTAINER Christian Mehlmauer <FireFart@gmail.com>

RUN adduser -h /ripe -g ripe -D ripe

COPY . /ripe
WORKDIR /ripe

RUN apk update && \
    apk add \
      postgresql-libs \
    && apk add --virtual .builddeps \
      build-base \
      postgresql-dev \
    && pip install -r requirements.txt \
    && apk del .builddeps \
    && rm -rf /var/cache/apk/*

RUN chown -R ripe:ripe /ripe
USER ripe

RUN ./download_dumps.sh

ENTRYPOINT ["/ripe/create_ripe_db.py"]
CMD ["--help"]
