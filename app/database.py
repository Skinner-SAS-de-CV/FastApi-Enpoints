from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener la URL de PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
print ("DATABASE_URL:", DATABASE_URL)

# Verificar que DATABASE_URL se cargó correctamente
if not DATABASE_URL:
    raise ValueError("ERROR: La variable de entorno DATABASE_URL no está configurada correctamente.")


# Configurar SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    title = Column(Text, index=True, nullable=False)
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
    
#Analisis
class Analize(Base):
    __tablename__ = "analisis"
    id = Column(Integer, primary_key=True, index=True)
    feedback = Column(Text, index=True, nullable=False)
    match_score = Column(Float)
    decision = Column(String)
    file_name = Column(String)
    job_title = Column(String)
    name = Column(String)
    
    

# tabla del  candidato
class Candidate(Base):
     __tablename__ = "candidatos"
     id = Column(Integer, primary_key=True, index=True)
     name = Column(String, nullable=False)
     birthday = Column(String, nullable=False)
     country = Column(String, nullable=False)
     # este nivel_id es para relacionar cuando seleccionas si sos estudiante, junior, senior o experto
     # en el servicio...
     nivel_id = Column(Integer, ForeignKey("nivel_educativo.id", ondelete="CASCADE"), nullable=False)
    
#  Se relaciona con el trabajo.
     nivel = relationship("Nivel", back_populates="candidatos")
    
    
# tabla del  nivel de profesion/educacion
class Nivel(Base):
    __tablename__ = "nivel_educativo"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    candidatos = relationship("Candidate", back_populates="nivel")
    
# contactos
class Contact(Base):
    __tablename__ = "contactos"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    name_company = Column(String, nullable=False)
    email = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
        
#Crear las tablas en PostgreSQL
def create_tables():
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("¡Tablas creadas correctamente!")

if __name__ == "__main__":
    create_tables()
