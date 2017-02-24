FROM python:3.5
EXPOSE 3031
COPY app/requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt
COPY app /app
CMD ["uwsgi", "uwsgi.ini"]
