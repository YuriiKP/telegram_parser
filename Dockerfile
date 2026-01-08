FROM python:3.12-slim

WORKDIR /bot 

# Установка компилятора и инструментов сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p data accounts && chmod -R 777 data accounts

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . . 

CMD ["python", "main.py"]