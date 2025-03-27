import os
import uvicorn
import PyPDF2
import docx2txt
import re
from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Function, Profile, SessionLocal, Client, Job, Skill

# Cargar variables de entorno
load_dotenv(override=True)

# Verificar que la API Key de OpenAI está configurada
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("ERROR: La API Key de OpenAI no se encontró.")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", 'https://api.openai.com')
client = OpenAI(base_url = OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

print("API Key cargada en el backend:", os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# Conexion con la base de datos.
def get_db():
    db= SessionLocal()
    try:
        yield db
    finally: 
        db.close()


FRONTEND_URL = os.getenv("FRONTEND_URL") 

origins = ["http://localhost:3000", FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"], 
)

# Modelo NLP para similitud semántica.
model = SentenceTransformer("all-MiniLM-L6-v2")


#Endpoint para **añadir trabajos y habilidades**
@app.post("/agregar_trabajo/")
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

# Función para calcular la similitud semántica entre el CV y la descripción del trabajo
def match_resume_to_job(resume_text: str, funciones_del_trabajo: str) -> float:
    embeddings = model.encode([resume_text, funciones_del_trabajo], convert_to_tensor=True)
    score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    return round(score, 2)

# Generar un feedback detallado usando GPT-4o-mini
def generate_gpt_feedback(resume_text: str, nombre_del_cliente: str, funciones_del_trabajo: str, perfil_del_trabajador: str) -> str:

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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Eres un experto en selección de talento humano."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


#Analizar un CV y obtener políticas del cliente
@app.post("/analyze/")
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

    # Obtener habilidades del trabajo
    #skills = [s.name for s in db.query(Skill).filter(Skill.job_id == job.id).all()]

    # Obtener funciones del trabajo
    # con el fragmento de codigo abajo  obtengo las funciones del trabajo pero si no
    #tengo datos me puede causar a un error por eso lo cambie en ves de query hice un join.
    # funciones_del_trabajo = ", ".join([f.title for f in db.query(Function).filter(Function.job_id == job.id).all()])
    funciones_del_trabajo = ", ".join([f.title for f in job.functions]) if job.functions else "No especificado"

    # Obtener perfil del trabajador
    perfil_del_trabajador = ", ".join([p.name for p in db.query(Profile).filter(Profile.job_id == job.id).all()])

    # Extraer texto del CV
    resume_text = extract_text(file)

   
    feedback = generate_gpt_feedback(resume_text, client.name, funciones_del_trabajo, perfil_del_trabajador)

    match_score = match_resume_to_job(resume_text, funciones_del_trabajo)
    

    # Ajuste en la decisión basado en el match_score
    if match_score >= 0.6:
        
        decision = "Puntaje Alto"
        
    elif match_score >= 0.5:
        
        decision = "Puntaje Promedio"
    else:
        decision = "Puntaje Bajo"

    return {
        
        "file_name": file.filename,
        "job_title": job.title,
        "match_score": match_score,
        "decision": decision,
        "feedback": feedback if feedback is not None else "No se pudo generar feedback"
        }


# Verificación de que FastAPI está funcionando en producción
@app.get("/")
def read_root():
    return {"message": "🚀 FastAPI funcionando correctamente en Railway!"}

# Configuración para producción
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
