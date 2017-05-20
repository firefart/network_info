FROM python:3-alpine
MAINTAINER Christian Mehlmauer <FireFart@gmail.com>

ENV USERNAME app
ENV APP_HOME /app

RUN adduser -h $APP_HOME -g $USERNAME -D $USERNAME

WORKDIR $APP_HOME

COPY requirements.txt $APP_HOME

RUN apk update && \
    apk add \
      bash \
      postgresql-libs \
    && apk add --virtual .builddeps \
      build-base \
      postgresql-dev \
    && pip install -r requirements.txt \
    && apk del .builddeps \
    && rm -rf /var/cache/apk/*

COPY . $APP_HOME
RUN chown -R $USERNAME:$USERNAME $APP_HOME
USER $USERNAME

RUN mkdir -p databases

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["--help"]
