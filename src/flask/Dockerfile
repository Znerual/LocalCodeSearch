FROM python:3.11

ADD LocalCodeSearch/requirements.txt /app/LocalCodeSearch/requirements.txt
RUN pip install -r /app/LocalCodeSearch/requirements.txt 

ADD LocalCodeSearch /app/LocalCodeSearch

# --no-cache-dir

ENV PATH /usr/local/bin:$PATH

EXPOSE 3000

WORKDIR /app/LocalCodeSearch

CMD [ "python", "wsgi.py" ]
