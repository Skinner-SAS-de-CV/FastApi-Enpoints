from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware  
import PyPDF2
import docx2txt
import re
from sentence_transformers import SentenceTransformer, util
import openai
from dotenv import load_dotenv
import os

import uvicorn

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise ValueError("⚠️ ERROR: La API Key de OpenAI no se encontró. Verifica tu archivo .env")

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "FastAPI está funcionando en Railway 🚀"}

if __name__ == "__main__":
    
    port = int(os.getenv("PORT", 8000))  # aca lo lee desde Railwail
    uvicorn.run(app, host="0.0.0.0", port=port)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # solo para pruebas cambiar a produccion 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo NLP para similitud semántica
model = SentenceTransformer("all-MiniLM-L6-v2")

# Lista de habilidades
SKILLS_LIST = {
    "python", "java", "javascript", "sql", "machine learning", "data analysis",
    "react", "aws", "licenciado en Administracion de Empresas", "Economista",
    "Auditor", "Cloud Computing", "Inteligencia Artificial", "Gestión de personas", 
    "Diseño UX", "Desarrollo de aplicaciones móviles", "Producción de video",
    "Liderazgo de ventas", "Traducción", "Producción de audio", "Procesamiento del lenguaje natural",
    "Trabajar en equipo", "Resolver conflictos y problemas", "Capacidad de tomar decisiones",
    "Adaptación al cambio", "Capacidad de comunicar eficazmente", "Proactividad", "Empatía",
    "Creatividad", "Tolerancia a la presión", "Orientación a resultados",  
    "Compromiso", "Capacidad de Aprendizaje", "Innovación", "Impacto/Influencia", "Resolución sostenible de conflictos"
}

# Función para extraer texto del archivo
def extract_text(file: UploadFile) -> str:
    text = ""
    if file.filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file.file)
        text = " ".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
    elif file.filename.endswith(".docx"):
        text = docx2txt.process(file.file)
    return text.lower()

# Extrae habilidades según la lista predefinida
def extract_skills(text: str) -> list:
    return [skill for skill in SKILLS_LIST if skill in text]

# Extrae experiencia usando expresiones regulares
def extract_experience(text: str) -> list:
    experience = re.findall(r"(\d+)\s*(?:años|years)", text)
    return experience if experience else []

# Calcula la similitud semántica entre el CV y la descripción del trabajo
def match_resume_to_job(resume_text: str, job_desc: str) -> float:
    embeddings = model.encode([resume_text, job_desc], convert_to_tensor=True)
    score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    return round(score, 2)

client = openai.OpenAI()  # Crear instancia del cliente OpenAI

def generate_gpt_feedback(resume_text: str, job_desc: str) -> str:
    """Genera un análisis del currículum usando GPT-4."""
    prompt = f"""
    Analiza el siguiente currículum en comparación con la descripción del trabajo.
    - Resume los puntos fuertes y débiles del candidato.
    - Explica si tiene las habilidades requeridas o no.
    - Da recomendaciones para mejorar su perfil.

    --- Currículum ---
    {resume_text}

    --- Descripción del Trabajo ---
    {job_desc}

    Proporciona un análisis claro y detallado.
    """

    response = client.chat.completions.create(  # esto se usa ahora para llamar a OpenAI
        model="gpt-4",
        messages=[{"role": "system", "content": "Eres un experto en selección de talento."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content  # y nueva forma para acceder al contenido

# Endpoint para analizar un currículum
@app.post("/analyze_resume/")
async def analyze_resume(file: UploadFile = File(...), job_desc: str = ""):
    resume_text = extract_text(file)
    skills = extract_skills(resume_text)
    experience = extract_experience(resume_text)
    match_score = match_resume_to_job(resume_text, job_desc)
    feedback = generate_gpt_feedback(resume_text, job_desc)

    result = {
        "file_name": file.filename,
        "match_score": match_score,
        "skills": skills,  
        "experience": experience,
        "decision": "Selected" if match_score > 0.7 else "No fue seleccionado",
        "reason": "Good match" if match_score > 0.7 else "Falta de experiencia o habilidades relevantes",
        "feedback": feedback
    }

    return result
