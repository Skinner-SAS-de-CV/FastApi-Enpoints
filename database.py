from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///./trabajos.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo Cliente
class Client(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    jobs = relationship("Job", back_populates="client")

# Modelo Trabajo
class Job(Base):
    __tablename__ = "tipos_de_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    client_id = Column(Integer, ForeignKey("clientes.id"))

    client = relationship("Client", back_populates="jobs")
    skills = relationship("Skill", back_populates="job")
    functions = relationship("Function", back_populates="job")  
    profile = relationship("Profile", back_populates="job")  

# Modelo Funciones del Trabajo
class Function(Base):
    __tablename__ = "funciones_del_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id"))

    job = relationship("Job", back_populates="functions")

# Modelo Perfil del Trabajo
class Profile(Base):
    __tablename__ = "perfil_del_trabajador"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id"))

    job = relationship("Job", back_populates="profile")

# Modelo Habilidades
class Skill(Base):
    __tablename__ = "habilidades"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id"))

    job = relationship("Job", back_populates="skills")

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)
