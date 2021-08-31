FROM python:3.9-slim-buster as base

WORKDIR /service

RUN pip install poetry
COPY . /service

RUN poetry install
CMD poetry run python ./raidsplit
