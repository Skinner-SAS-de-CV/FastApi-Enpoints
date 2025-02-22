from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv

# 🔹 Cargar variables de entorno
load_dotenv(override=True)

#Configurar la conexión a PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

#Crear la conexión con SQLAlchemy
engine = create_engine(DATABASE_URL, echo=True)  # `echo=True` muestra las consultas en consola (para debugging)

#Configurar la sesión de la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#Base para los modelos
Base = declarative_base()

#Modelo Cliente
class Client(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    jobs = relationship("Job", back_populates="client", cascade="all, delete")

#Modelo Trabajo
class Job(Base):
    __tablename__ = "tipos_de_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)

    client = relationship("Client", back_populates="jobs")
    skills = relationship("Skill", back_populates="job", cascade="all, delete")
    functions = relationship("Function", back_populates="job", cascade="all, delete")
    profile = relationship("Profile", back_populates="job", cascade="all, delete")

#Modelo Funciones del Trabajo
class Function(Base):
    __tablename__ = "funciones_del_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    job = relationship("Job", back_populates="functions")

#Modelo Perfil del Trabajo
class Profile(Base):
    __tablename__ = "perfil_del_trabajador"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    job = relationship("Job", back_populates="profile")

#Modelo Habilidades
class Skill(Base):
    __tablename__ = "habilidades"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    job = relationship("Job", back_populates="skills")

#Crear las tablas en PostgreSQL
def create_tables():
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("¡Tablas creadas correctamente!")

if __name__ == "__main__":
    create_tables()
