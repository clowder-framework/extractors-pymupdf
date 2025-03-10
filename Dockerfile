FROM python:3.10

RUN apt-get update

COPY requirements.txt ./
RUN pip install -r requirements.txt --no-cache-dir

COPY extractor_info.json extractor.py ./

CMD ["python3", "extractor.py", "--heartbeat", "40"]
