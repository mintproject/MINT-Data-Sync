FROM python:3.7-alpine

COPY requirements.txt /requirements.txt

RUN pip install -r requirements.txt

COPY cronjobs /etc/crontabs/root

COPY sync.py /sync.py

CMD ["crond", "-f", "-d", "8"]

#CMD ["/bin/bash", "-c"]