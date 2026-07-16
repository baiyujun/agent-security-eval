FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /opt/m0a
COPY client.py /opt/m0a/client.py

CMD ["python", "-c", "import time; time.sleep(86400)"]
