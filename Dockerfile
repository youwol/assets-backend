FROM python:3.9-slim


RUN apt-get update \
    && apt-get install -y \
        ca-certificates brotli\
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8080
WORKDIR /root

COPY /requirements.txt /root/
RUN pip3 install --no-cache-dir --upgrade -r "requirements.txt"

COPY /src /root/


ENTRYPOINT ["python3.9", "-u", "main.py", "prod"]
