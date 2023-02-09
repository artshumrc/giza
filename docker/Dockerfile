FROM python:3.10-slim-buster as python-build
WORKDIR /app
RUN apt-get update --fix-missing
# g++ for Pillow; unixodbc-dev for pyodbc
RUN apt-get install -y nginx python-psycopg2 postgresql graphviz gettext gdal-bin python-gdal python3-numpy gnupg gpg libpq-dev gcc g++ unixodbc-dev

# Nginx tweaked
RUN addgroup --system nginx
RUN adduser --system nginx
RUN usermod -a -G nginx nginx
RUN mkdir -p /run/nginx

RUN mkdir -p /var/log/nginx && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stdout /var/log/nginx/error.log

# Use dev NGINX config
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Python requirements
COPY requirements.txt /app
RUN pip install -r requirements.txt

# App files, including built frontend from static stage (actually no because this uses static)
COPY giza /app/giza
COPY tms /app/tms
COPY search /app/search
COPY utils /app/utils
COPY static /app/static
COPY templates /app/templates
COPY manage.py /app/manage.py

# Setup
RUN mkdir /app/setup
WORKDIR /app/setup
COPY docker/postgres_ready.py /app/setup
RUN sed -i 's/\r$//g' postgres_ready.py
RUN chmod +x postgres_ready.py
COPY docker/entrypoint /app/setup
RUN sed -i 's/\r$//g' entrypoint
RUN chmod +x entrypoint

ENV PYTHONUNBUFFERED 1
ENV MIGRATE 0

EXPOSE 8000 5000

WORKDIR /app
CMD setup/entrypoint