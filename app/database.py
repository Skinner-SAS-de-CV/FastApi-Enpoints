import enum as python_enum
from sqlalchemy import create_engine, Enum, Boolean, Numeric, Index, Column, String, Integer, ForeignKey, Text, DateTime, Float, Date, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
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


# Enum

class PlanSlug(str, python_enum.Enum):
    FREE = "FREE"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    BIANNUAL = "BIANNUAL"
    PREMIUM = "PREMIUM"
    FULL_ACCESS = "FULL_ACCESS"

class SubscriptionStatus(str, python_enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


# Modelo planes para empresas

class Plan(Base):
    __tablename__ = "planes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(Enum(PlanSlug), nullable=False, unique=True)
    name = Column(String, nullable=False)
    price_usd = Column(Numeric(10, 2), nullable=False)
    analyses_limit = Column(Integer, nullable=True) #None = ilimitado
    reports_limit = Column(Integer, nullable=True) #None = ilimitado
    duration_days = Column(Integer, nullable=True)
    is_active     = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subscriptions = relationship("Subscription", back_populates="plan")    

#Modelo Suscripcion (Ligada al Cliente/Empresa)

class Subscription(Base):
    __tablename__ = "suscripciones"
    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id     = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False)
    plan_id       = Column(Integer, ForeignKey("planes.id", ondelete="RESTRICT"), nullable=False)
    status        = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING, nullable=False)
    analyses_used = Column(Integer, default=0, nullable=False)
    reports_used  = Column(Integer,default=0, nullable=False)
    starts_at     = Column(DateTime, nullable=True)
    expires_at    = Column(DateTime, nullable=True)

    # Quien activo la suscripcion manualmente
    activated_by  = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)
    activated_at  = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    plan          = relationship("Plan", back_populates="subscriptions")
    client        = relationship("Client", back_populates="subscriptions")
    topups        = relationship("AnalysisTopup", back_populates="subscription")

    __table_args__ = (
        Index('ix_suscripciones_client_id', 'client_id'),
        Index('ix_suscripciones_status', 'status'),
        Index('ix_suscripciones_expires_at', 'expires_at'),
    )

#Modelo Topup (paquetes de 50 adicionales)

class AnalysisTopup(Base):
    __tablename__ = "topups_analisis"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id  = Column(Integer, ForeignKey("suscripciones.id", ondelete="CASCADE"), nullable=False)
    analysis_added   = Column(Integer, default=50, nullable=False)
    price_usd        = Column(Numeric(10, 2), nullable=False)
    status           = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.PENDING, nullable=False)
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subscription     = relationship("Subscription", back_populates="topups")


#Modelo Cliente(Empresas)
class Client(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    external_organization_id = Column(String, nullable=True)
    contact_email = Column(String, nullable=True) #para notificaciones
    contact_phone = Column(String, nullable=True)
    
    users = relationship("User", back_populates="client", cascade="all, delete")
    jobs = relationship("Job", back_populates="client", cascade="all, delete")
    subscriptions = relationship("Subscription", back_populates="client")
    
 #Modelo Usuario
class User(Base):
    __tablename__ = "usuario"
    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String, index=True, nullable=False)
    lastname = Column(String, index=True, nullable=False)
    external_user_id = Column(String, nullable=False, unique=True)
    client_id = Column(Integer, ForeignKey("clientes.id", ondelete="RESTRICT"),nullable=False)

    client = relationship("Client", back_populates="users")
    
    
    

#Modelo Trabajo
class Job(Base):
    __tablename__ = "tipos_de_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc)) 
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    client = relationship("Client", back_populates="jobs")
    skills = relationship("Skill", back_populates="job", cascade="all, delete")
    functions = relationship("Function", back_populates="job", cascade="all, delete")
    profile = relationship("Profile", back_populates="job", cascade="all, delete")
    analisis = relationship("Analize", back_populates="job", cascade="all, delete")

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
    name = Column(Text, nullable=False)
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    job = relationship("Job", back_populates="profile")

#Modelo Habilidades
class Skill(Base):
    __tablename__ = "habilidades"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    job = relationship("Job", back_populates="skills")
    
#Analisis
class Analize(Base):
    __tablename__ = "analisis"
    id = Column(Integer, primary_key=True, index=True)
    feedback = Column(Text, nullable=False)
    match_score = Column(Float)
    decision = Column(String)
    file_name = Column(String)
    job_title = Column(String)
    name = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    job_id = Column(Integer, ForeignKey("tipos_de_trabajo.id", ondelete="CASCADE"), nullable=False)

    job = relationship("Job", back_populates="analisis")
    
    

# tabla del  candidato
class Candidate(Base):
     __tablename__ = "candidatos"
     id = Column(Integer, primary_key=True, index=True)
    # Id de usuario en clerk
     external_user_id = Column(String, nullable=False, unique=True)
     firstname = Column(String, nullable=False)
     lastname = Column(String, nullable=False)
     birthday = Column(Date, nullable=False)
     country = Column(String, nullable=False)
     # este nivel_id es para relacionar cuando seleccionas si sos estudiante, junior, senior o experto
     # en el servicio...
     nivel_id = Column(Integer, ForeignKey("nivel_educativo.id", ondelete="CASCADE"), nullable=False)
    
#  Se relaciona con el trabajo.
     nivel = relationship("Nivel", back_populates="candidatos")
    
    
# tabla del  nivel de educacion
class Nivel(Base):
    __tablename__ = "nivel_educativo"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    
    
    candidatos = relationship("Candidate", back_populates="nivel")
    
    
# tabla para contabilizar el uso de la app.
class Usage(Base):
    __tablename__ = "uso_de_la_app"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("candidatos.id"), nullable=False, unique=True)
    usage_count = Column(Integer, default=0, nullable=False)
    usage_limit = Column(Integer, nullable=False)
    last_reset = Column(DateTime, default=lambda: datetime.now(timezone.utc)) # para llevar el control de cuando se resetea el contador no se si es necesario.
    

# contactos
class Contact(Base):
    __tablename__ = "contactos"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    name_company = Column(String, nullable=False)
    email = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        
#Crear las tablas en PostgreSQL
def create_tables():
    print("Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("¡Tablas creadas correctamente!")

if __name__ == "__main__":
    create_tables()
