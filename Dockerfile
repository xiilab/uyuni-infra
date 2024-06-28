FROM python:3.11.9-slim

WORKDIR /usr/src/app

RUN apt update && apt install -y sshpass

COPY kubespray/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


