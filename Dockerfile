FROM python:3.9.0-alpine3.12

RUN pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

COPY ./requirements.txt ./requirements.txt

RUN pip install -r requirements.txt

COPY ./transformer.py ./transformer.py

WORKDIR /conf

ENTRYPOINT ["python", "/transformer.py",  "--input", "./export.json", "--configuration", "./config.json"]
