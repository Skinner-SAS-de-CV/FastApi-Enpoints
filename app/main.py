import os
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
from database import Function, Profile, SessionLocal, Client, Job, Skill, Contact
from pydantic import BaseModel, EmailStr, field_validator
import bleach
from openai import AsyncOpenAI
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uuid
from config import ORIGINS, OPENAI_API_KEY, OPENAI_BASE_URL
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText

# segun lo que lei y con chatgpt hacemos un executor para manejar las tareas asincronas globales.
executor = ThreadPoolExecutor()
from auth import is_signed_in

# Definiendo los alcances requeridos
ALCANCES = ['https://www.googleapis.com/auth/gmail.send']


# Cargar variables de entorno
load_dotenv(override=True)

# Obtener la dirección de correo electrónico desde las variables de entorno
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')

# Verificar que la API Key de OpenAI está configurada
if not OPENAI_API_KEY:
    raise ValueError("ERROR: La API Key de OpenAI no se encontró.")

async_client = AsyncOpenAI(base_url = OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

print("API Key cargada en el backend:", os.getenv("OPENAI_API_KEY"))

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
# ENDPOINTS
# ==========================================================

#Endpoint para **añadir trabajos y habilidades**
@app.post("/agregar_trabajo/", dependencies=[Depends(check_signed_in)])
async def agregar_trabajo(
    nombre_del_cliente: str = Form(...),
    titulo_de_trabajo: str = Form(...),
    perfil_del_trabajador: str = Form(...),  
    funciones_del_trabajo: str = Form(...),
    habilidades: str = Form(...),  
    db: Session = Depends(get_db)
):
    
    print("📩 Recibiendo solicitud con los siguientes datos:")
    print(f"Cliente: {nombre_del_cliente}")
    print(f"Trabajo: {titulo_de_trabajo}")
    print(f"Perfil: {perfil_del_trabajador}")
    print(f"Funciones: {funciones_del_trabajo}")
    print(f"Habilidades: {habilidades}")
    
    #Buscar si el cliente ya existe
    client = db.query(Client).filter(Client.name == nombre_del_cliente).first()
    if not client:
        client = Client(name=nombre_del_cliente)
        db.add(client)
        db.flush()
        db.commit()
        db.refresh(client)

    #Crear un nuevo trabajo
    job = Job(title=titulo_de_trabajo, client_id=client.id)
    db.add(job)
    db.flush()
    db.commit()
    db.refresh(job)

    # Guardar habilidades en la base de datos
    for skill in habilidades.split(","):
        db.add(Skill(name=skill.strip(), job_id=job.id))

    # Guardar perfil en la base de datos
    db.add(Profile(name=perfil_del_trabajador.strip(), job_id=job.id))

    # Guardar funciones del trabajo en la base de datos
    for function in funciones_del_trabajo.split(","):
        db.add(Function(title=function.strip(), job_id=job.id))
        
    db.flush()
    db.commit()
    return {"message": "Trabajo, habilidades, perfil y funciones registradas exitosamente"}

# Endpoint para obtener clientes
@app.get("/clients/")
async def get_clients(db: Session = Depends(get_db)):
    client_names = db.query(Client).all()
    return [{"name": c.name, "id": c.id} for c in client_names]

# Endpoint para **obtener trabajos por cliente usando id de cliente**
@app.get("/obtener_trabajos_por_cliente/{id}")
async def obtener_trabajos_por_cliente(id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == id).one_or_none()
    if not client:
        return {"error": "Cliente no encontrado"}

    jobs = db.query(Job).filter(Job.client_id == client.id).all()
    return [{"id": job.id, "title": job.title} for job in jobs]


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
async def generate_gpt_feedback_async(analysis_id: str = Form(...), resume_text: str = Form(...), nombre_del_cliente: str = (Form(...)), funciones_del_trabajo: str = Form(...), perfil_del_trabajador: str = Form(...)) -> str:

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

    ** Formato de respuesta esperado:**
    - **Puntos Fuertes:** 
    - **Puntos Débiles:** 
    - **Cumplimiento con el perfil:** 
    - **Recomendación final:**
    """

    response = await async_client.responses.create(
        model="gpt-4o-mini",
        input=[{"role": "system", "content": "Eres un experto en selección de talento humano."},
                  {"role": "user", "content": prompt}]
    )
    
    feedback_text = response.output_text
     
    return{"analysis_id": analysis_id, "feedback": feedback_text}

# ==========================================================
# Funcion para enviar un correo electrónico y notificación usando la API de Gmail.
# el archivo token.json(Credenciales del usuario). Almacena el access_token y, opcionalmente, el refresh_token obtenidos
# después de que el usuario autoriza a la aplicación.Se genera automáticamente por la aplicación después de 
# completar el flujo de autorización con credentials.json.
# ==========================================================
def get_gmail_servicios():
    credenciales = None
    if os.path.exists('token.json'):
        credenciales = Credentials.from_authorized_user_file('token.json', ALCANCES)
    if not credenciales or not credenciales.valid:
        if credenciales and credenciales.expired and credenciales.refresh_token:
            credenciales.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ALCANCES)
            credenciales = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(credenciales.to_json())
    service = build('gmail', 'v1', credentials=credenciales)
    return service


def send_notification_email(contact):
    service = get_gmail_servicios()
    message_text = f"""
    Se ha recibido un nuevo mensaje de contacto:

    Nombre: {contact.name}
    Nombre_Empresa: {contact.name_company}
    Email: {contact.email}
    Mensaje: {contact.message}
    """
    message = MIMEText(message_text)
    message['to'] = EMAIL_ADDRESS
    message['from'] = EMAIL_ADDRESS
    message['subject'] = 'Nuevo contacto recibido'

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw_message}

    try:
        message = service.users().messages().send(userId='me', body=body).execute()
        print(f'Mensaje enviado: {message["id"]}')
    except Exception as error:
        print(f'Ocurrió un error: {error}')

# ==========================================================
# Analizar un CV y obtener políticas del cliente
# ==========================================================

@app.post("/analyze/", dependencies=[Depends(check_signed_in)])
async def analyze_resume(
    file: UploadFile = File(...),
    job_id: int = Form(...),
    client_id: int = Form(...),
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

    # Ajuste en la decisión basado en el match_score
    if match_score >= 0.6:
        
        decision = "Puntaje Alto"
        
    elif match_score >= 0.5:
        
        decision = "Puntaje Promedio"
    else:
        decision = "Puntaje Bajo"

    analysis_id = str(uuid.uuid4())

    return {
        "analysis_id": analysis_id,
        "file_name": file.filename,
        "job_title": job.title,
        "match_score": match_score,
        "decision": decision,
        "feedback": feedback if feedback is not None else "No se pudo generar feedback"
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
    
    
# Configuración para producción
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
