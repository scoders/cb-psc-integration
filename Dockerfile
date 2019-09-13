FROM python:3.7-alpine

WORKDIR /cb

RUN apk add --no-cache postgresql-dev git openssh gcc musl-dev make libxml2-dev libxslt-dev 

# to avoid fetchin packages on code edits
COPY requirements.txt .
RUN pip install -r requirements.txt     

COPY . .
RUN pip install .
CMD make serve
