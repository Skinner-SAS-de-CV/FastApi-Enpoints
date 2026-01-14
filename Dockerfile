FROM python:3.12

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# modelo FastText para detección de idioma
RUN mkdir -p /opt/models && \
    wget -4 -O /opt/models/lid.176.bin https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin

COPY ./app /app/app

CMD uvicorn main:app --port ${PORT:-80} --app-dir app --host 0.0.0.0
