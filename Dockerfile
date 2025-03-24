
FROM python:3.10
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
# Adicionar archivo de variables del entorno
COPY ./.env /code/app/.env

EXPOSE 80

CMD ["fastapi", "run", "app/main.py", "--port", "80"]