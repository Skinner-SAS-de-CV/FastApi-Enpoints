from datetime import datetime
import os
from pydoc import text
from typing import List, Optional
import uvicorn
import PyPDF2
import docx2txt
import re
from fastapi import FastAPI, UploadFile, File, Form, Depends, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Analize, Function, Profile, SessionLocal, Client, Job, Skill, Contact, Candidate, Nivel, Usage
import smtplib
from email.message import EmailMessage
from pydantic import BaseModel, EmailStr, field_validator
import bleach
from openai import AsyncOpenAI
import asyncio
from concurrent.futures import ThreadPoolExecutor
from config import ORIGINS, OPENAI_API_KEY, OPENAI_BASE_URL

# acá pongo la clase de  AnalizeSchema.
class AnalizeSchema(BaseModel):
    id: int
    name: str
    job_title: str
    match_score: float
    feedback: str    
    decision: str
    file_name: str
    created_at: datetime
    class Config:
        orm_mode = True

# segun lo que lei y con chatgpt hacemos un executor para manejar las tareas asincronas globales.
executor = ThreadPoolExecutor()
from auth import is_signed_in, request_state_payload


# Cargar variables de entorno
load_dotenv(override=True)

# Verificar que la API Key de OpenAI está configurada
if not OPENAI_API_KEY:
    raise ValueError("ERROR: La API Key de OpenAI no se encontró.")

async_client = AsyncOpenAI(base_url = OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

print("API Key cargada en el backend:", OPENAI_API_KEY)

app = FastAPI()

# Conexion con la base de datos.
def get_db():
    db= SessionLocal()
    try:
        yield db
    finally: 
        db.close()


async def check_signed_in(request: Request):
    if not is_signed_in(request):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

# Modelo NLP para similitud semántica.
model = SentenceTransformer("all-MiniLM-L6-v2")

# ==========================================================
# VALIDACIÓN Y SANITIZACIÓN DEL FORMULARIO DE CONTACTO
# ==========================================================

class ContactForm(BaseModel):
    name: str
    name_company: str
    email: EmailStr
    message: str

    @field_validator("name")
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v
    
    @field_validator("name_company")
    def name_company_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v

    @field_validator("message")
    def message_must_have_min_length(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("El mensaje debe tener al menos 10 caracteres")
        # Sanitizamos el mensaje para eliminar etiquetas HTML potencialmente maliciosas
        #está es una buena práctica para evitar ataques XSS
        # y otros problemas de seguridad.
        #así que lo hacemos con la librería bleach.
        return bleach.clean(v)

# Dependency para extraer y validar los datos del formulario
def as_contact_form(
    name: str = Form(...),
    name_company: str = Form(...),
    email: str = Form(...),
    message: str = Form(...)
):
    return ContactForm(name=name, name_company=name_company, email=email, message=message)

# ==========================================================
# Funciones para analizar el CV y generar feedback
# ==========================================================

# Función para extraer texto de un archivo PDF o DOCX
def extract_text(file: UploadFile) -> str:
    text = ""
    if file.filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file.file)
        text = " ".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
    elif file.filename.endswith(".docx"):
        text = docx2txt.process(file.file)
    return text.lower()  # Convertir todo a minúsculas para evitar errores de coincidencia

# Función para extraer experiencia en años usando expresiones regulares
def extract_experience(text: str) -> list:
    experience = re.findall(r"(\d+)\s*(?:años|years)", text)
    return experience if experience else []

# Función para calcular la similitud semántica entre el CV y la descripción del trabajo y el ThreadPoolExecutor
def match_resume_to_job_sync(resume_text: str, funciones_del_trabajo: str) -> float:
    embeddings = model.encode([resume_text, funciones_del_trabajo], convert_to_tensor=True)
    score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    return round(score, 2)

async def match_resume_to_job_async(resume_text: str, funciones_del_trabajo: str) -> float:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, match_resume_to_job_sync, resume_text, funciones_del_trabajo)

# Generar un feedback detallado usando GPT-4o-mini
async def generate_gpt_feedback_async(resume_text: str = Form(...), nombre_del_cliente: str = (Form(...)), funciones_del_trabajo: str = Form(...), perfil_del_trabajador: str = Form(...)) -> str:

    prompt = f"""
    Un cliente llamado **{nombre_del_cliente}** está buscando contratar a un candidato para un puesto específico. 
    Este cliente tiene las siguientes políticas y requisitos de contratación:

    --- Funciones del Cliente ---
    
   - Lee la base de datos segun **{nombre_del_cliente}** que a sugerido para el puesto de trabajo.
    

    --- 🎯 Perfil del Candidato Requerido ---
    - Analisa el **{perfil_del_trabajador}** si cumple con las habilidades del puesto de trabajo.
    

    --- 🏢 Descripción del Trabajo ---
    
    -Analisa si el candidato cumple con la **{funciones_del_trabajo}**.
    

    --- 📄 Currículum del Candidato ---
    {resume_text}

    **Tareas a realizar:**
    - Resume los puntos fuertes y débiles del candidato.
    - Explica si tiene las habilidades requeridas o no.
    - Analiza si cumple con las funciones y requisitos del cliente.
    - Da una recomendación final sobre si el candidato es adecuado para el puesto segun con el match_core.
    -Si el CV está en inglés, la retroalimentación también se brinde en inglés profesionalmente.

    ** Formato de respuesta esperado:**
    - **Puntos Fuertes:** 
    - **Puntos Débiles:** 
    - **Cumplimiento con el perfil:** 
    - **Recomendación final:**
    """

    response = await async_client.responses.create(
        model="gpt-5-mini",
        input=[{"role": "system", "content": "Eres un experto en selección de talento humano. Actúa como un asesor experto para seleccionar al mejor personal para las empresas, eres experto en redacción y analisis de currículums profesionales en inglés y español o cualquier otro idioma y da el feedback ya sea en inglés o español o cualquier otro idioma."},
                  {"role": "user", "content": prompt}]
    )
    
    feedback_text = response.output_text
     
    return{"feedback": feedback_text}

# ==========================================================
# Funcion para enviar un correo electrónico y notificación etc...
# ==========================================================

def send_notification_email(contact: Contact):
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("No se configuró EMAIL_ADDRESS o EMAIL_PASSWORD asi que hazlo")
        return

    msg = EmailMessage()
    msg['Subject'] = "Nuevo contacto recibido"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS  
    msg.set_content(f"""
    Se ha recibido un nuevo mensaje de contacto:

    Nombre: {contact.name}
    Nombre_Empresa: {contact.name_company}
    Email: {contact.email}
    Mensaje: {contact.message}
    """)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("Email enviado correctamente.")
    except Exception as e:
        print(f"Error al enviar email: {e}")


# ==========================================================
# Analizar un CV y obtener políticas del cliente
# ==========================================================

def puntuacion(match_score: float):
    
    score = match_score * 10  
    # Calificacion vieja
    if score >= 6.0:
        score = min(10, score + 1.5)
    elif 5.0 <= score < 6.0:
        score += 1.0
    elif 4.0 <= score < 5.0:
        score += 0.75

    # Calificacion nueva
    if score >= 8.0:
        decision = "Alto"
    elif 7.0 <= score < 8.0:
        decision = "Promedio Alto"
    elif 6.0 <= score < 7.0:
        decision = "Promedio Bajo"
    elif 4.0 <= score < 6.0:
        decision = "Bajo"
    else:
        decision = "Deficiente"

    return round(score, 2), decision

@app.post("/analyze/", dependencies=[Depends(check_signed_in)])
async def analyze_resume(
    file: UploadFile = File(...),
    job_id: int = Form(...),
    client_id: int = Form(...),
    nombre_del_candidato: str = Form(...),
    db: Session = Depends(get_db)
):
    # Obtener el cliente
    client = db.query(Client).filter(Client.id == client_id).one_or_none()
    if not client:
        return {"error": "Cliente no encontrado"}

    # Obtener el trabajo desde la base de datos
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    if not job:
        return {"error": "Trabajo no encontrado"}

    funciones_del_trabajo = ", ".join([f.title for f in job.functions]) if job.functions else "No especificado"

    # Obtener perfil del trabajador
    perfil_del_trabajador = ", ".join([p.name for p in db.query(Profile).filter(Profile.job_id == job.id).all()])

    
    
    # Extraer texto del CV
    resume_text = extract_text(file)

    # lanzo la tareas asíncrona con TaskGroup
    # para calcular match_score y generar el feedback de chatGPT

    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(
            generate_gpt_feedback_async(resume_text, client.name, funciones_del_trabajo, perfil_del_trabajador))
        task2 = tg.create_task(
            match_resume_to_job_async(resume_text, funciones_del_trabajo))

    # asignar los resultados de las funciones
    feedback =  task1.result()
    match_score = task2.result()
    
    puntuacion_calibrada, decision = puntuacion(match_score)
    print (feedback)
    
# Guardar el análisis en la base de datos
    new_analysis = Analize(
        feedback=feedback["feedback"],
        match_score=puntuacion_calibrada,
        decision=decision,
        file_name=file.filename,
        job_title=job.title,
        name=nombre_del_candidato,
        client_id=client_id
    )
    db.add(new_analysis)
    db.commit()

    return {
        "id": new_analysis.id,
        "file_name": file.filename, 
        "job_title": job.title,
        "match_score": puntuacion_calibrada,
        "name": new_analysis.name,
        "decision": decision,
        "feedback": feedback if feedback is not None else "No se pudo generar feedback",
        "created_at": new_analysis.created_at
        }

# Verificación de que FastAPI está funcionando en producción
@app.get("/")
def read_root():
    return {"message": "FastAPI funcionando correctamente en Railway!"}


# ==========================================================
# Aqui esta el endpoint para contactos
# ==========================================================

@app.post("/contactanos/")
async def create_contact(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    name_company: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    db: Session = Depends(get_db)
):
    new_contact = Contact(name=name, name_company=name_company, email=email, message=message)
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)

    # Aqui mandamos la notificacion al correo... 
    background_tasks.add_task(send_notification_email, new_contact)
    
    return {
        "message": "Tu mensaje ha sido recibido. ¡Pronto nos pondremos en contacto!",
        "contact": {"id": new_contact.id, "name": new_contact.name}
    }
# ==========================================================
# Aqui esta el endpoint de los perfiles
# ==========================================================
@app.put("/perfiles/{perfil_id}", dependencies=[Depends(check_signed_in)])
async def actualizar_perfil(
    perfil_id: int,
    firstname: str = Form(...),
    lastname: str = Form(...),
    birthday: datetime = Form(...),
    nivel_id: str = Form(...),
    country: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Actualizar un perfil existente.
    """
    perfil = db.query(Candidate).filter(Candidate.id == perfil_id).one_or_none()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    perfil.firstname = firstname
    perfil.lastname = lastname
    perfil.birthday = birthday.date()
    perfil.nivel_id = nivel_id
    perfil.country = country
    db.commit()
    db.refresh(perfil)

    return {"message": "Perfil actualizado exitosamente", "perfil": {"id": perfil.id, "name": perfil.firstname}}


@app.delete("/perfiles/{perfil_id}", dependencies=[Depends(check_signed_in)])
async def eliminar_perfil(perfil_id: int, db: Session = Depends(get_db)):
    """
    Eliminar un perfil existente.
    """
    perfil = db.query(Candidate).filter(Candidate.id == perfil_id).one_or_none()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    db.delete(perfil)
    db.commit()

    return {"message": "Perfil eliminado exitosamente"}

# ==========================================================
# Funcion para consultar los analisis de los candidatos.
# ==========================================================

@app.get("/analisis/", response_model=List[AnalizeSchema],dependencies=[Depends(check_signed_in)])
def listar_analisis(
    db: Session = Depends(get_db),
    name: Optional[str] = None,
    job_title: Optional[str] = None,
    order_by: Optional[str] = "match_score",
        ascending: Optional[bool] = False,
):
    query = db.query(Analize)

    if name:
        query = query.filter(Analize.name.ilike(f"%{name}%"))
    if job_title:
        query = query.filter(Analize.job_title.ilike(f"%{job_title}%"))

    order_field = getattr(Analize, order_by)
    query = query.order_by(order_field.asc() if ascending else order_field.desc())
    


    return query.all()



# Configuración para producción
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
