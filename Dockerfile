FROM python:3.7-alpine

WORKDIR /cb

RUN apk add --no-cache postgresql-dev git openssh gcc musl-dev make

COPY . .
RUN pip install .
CMD make serve
