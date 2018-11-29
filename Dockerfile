FROM poliez/cp-kafka-py-base:0.1.4-slim-stretch

LABEL maintainer.name="Raiden Map Team"
LABEL maintainer.email="info@raidenmap.io"

COPY pyproject.* .

RUN apt-get install -y --no-install-recommends \
        g++ ; \
    poetry config settings.virtualenvs.create false ; \
    poetry install --no-interaction --no-dev ; \
    apt-get purge g++  -y ; \
    apt-get autoremove -y ; \
    apt-get autoclean  -y ; \
    python get-poetry.py --uninstall ; \
    rm get-poetry.py ; \
    mkdir /app; 

WORKDIR /app

COPY ./raiden-events-poller .

CMD [ "python", "-u", "raiden_poller_cli.py" ]