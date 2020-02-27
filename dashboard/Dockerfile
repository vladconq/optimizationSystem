# базовый образ -> FROM <image>:<tag>
FROM python:3.7-slim

# выполнить и закоммитить
RUN mkdir /app
# рабочий каталог для всех инструкций
WORKDIR /app

RUN apt-get update \
    && apt-get install -y g++ python3-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# копирует файлы и добавляет в файловую систему контейнера
ADD requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
ADD . /app/

ENTRYPOINT [ "python" ]
CMD ["app.py"]