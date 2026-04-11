FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY src/ ./src/

RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt

COPY run.py ./

EXPOSE 8000

CMD ["python", "run.py"]
