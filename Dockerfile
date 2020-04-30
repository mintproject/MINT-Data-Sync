FROM python:3.7-alpine

COPY requirements.txt /requirements.txt

RUN pip install -r requirements.txt

COPY cronjobs /etc/crontabs/root

COPY sync_gldas.py /sync_gldas.py

CMD ["crond", "-f", "-d", "8"]