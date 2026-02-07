FROM mediapipe

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt

COPY *.py .
COPY *.json .

CMD ["python3", "main.py"]
