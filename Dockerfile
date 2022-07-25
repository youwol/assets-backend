FROM python:3.9-slim


RUN apt-get update \
    && apt-get install -y \
        ca-certificates brotli\
    && apt-get autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8080
WORKDIR /root

COPY /py-youwol/docker-requirements.txt /root/
RUN pip3 install --no-cache-dir --upgrade -r "docker-requirements.txt"

COPY /py-youwol/youwol_utils /root/youwol_utils
COPY /py-youwol/youwol_assets_backend /root/youwol_assets_backend
COPY /src /root/


ENTRYPOINT ["python3.9", "-u", "main.py", "prod"]
