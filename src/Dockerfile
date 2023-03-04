FROM python:3.11

ADD LocalCodeSearch /app/LocalCodeSearch

RUN pip install -r /app/LocalCodeSearch/requirements.txt --no-cache-dir

EXPOSE 3000

WORKDIR /app/LocalCodeSearch

CMD [ "python", "flask_server.py" ]
