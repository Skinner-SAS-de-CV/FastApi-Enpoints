# Skinner 

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Mako](https://img.shields.io/badge/Mako-FF6F00?style=for-the-badge)



  ![Skinner](./skinner-logo5.png)




# Skinner

Our recruitment system, powered by artificial intelligence, identifies and selects the ideal candidates, optimizing the hiring process and times.


---

## Description

We are dedicated to improving recruiting and hiring processes through advanced artificial intelligence. Our goal is to help companies find the best talent efficiently and accurately, transforming the way organizations build their teams.



# Como usar

## Directamente sin usar contenedor:
Creá un entorno virtual:
```
cd app
python -m venv <nombre_de_entorno>
```

Entrá en el nuevo entorno:

```
source skinner_virtual/bin/activate
```

Entrá en el `bin` e instala las librerias requeridas

```
pip install -r requirements.txt
```

- Comenzá la aplicación:

```

```

## Comenzar aplicación con Podman
Es necesario instalar docker o podman antes de comenzar.
En el directorio raíz:
```
podman-compose build
podman-compose up -d
```
Si querés recrear las imagenes:
```
podman-compose up --force-recreate -d
```

Para parar la aplicación:
```
podman-compose down
```

No he probado aún, pero para usar con docker, solo deberia ser cambiar `podman-compose` por `docker-compose`. Por ejemplo `docker compose up`