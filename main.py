import os
import uvicorn
import PyPDF2
import docx2txt
import re
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
from dotenv import load_dotenv


# Cargar variables de entorno
load_dotenv()

# Verificar que la API Key de OpenAI está configurada
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("⚠️ ERROR: La API Key de OpenAI no se encontró. Verifica tu archivo .env o las variables de entorno en Railway.")

client = OpenAI(api_key=OPENAI_API_KEY)

# Configurar FastAPI
app = FastAPI()

# Configurar CORS para permitir solo el frontend en producción
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://frontend-resume-analyzer.vercel.app") 

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # Permitir solo el frontend de Vercel
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Agregar OPTIONS
    allow_headers=["*"],
)

# Modelo NLP para similitud semántica
model = SentenceTransformer("all-MiniLM-L6-v2")

# Lista de habilidades predefinidas
SKILLS_LIST = {
    "python", "java", "javascript", "sql", "machine learning", "data analysis",
    "react", "aws", "administración de empresas", "economista", "auditor",
    "cloud computing", "inteligencia artificial", "gestión de personas",
    "diseño UX", "desarrollo de aplicaciones móviles", "producción de video",
    "liderazgo de ventas", "traducción", "producción de audio", "NLP",
    "trabajo en equipo", "resolución de problemas", "toma de decisiones",
    "adaptación al cambio", "comunicación efectiva", "proactividad", "empatía",
    "creatividad", "tolerancia a la presión", "orientación a resultados",
    "compromiso", "capacidad de aprendizaje", "innovación", "resolución de conflictos",
    "Metodología para realizar auditoría, supervisión y evaluaciónde la gestión de riesgos.",
    "Metodologías de gestión y medición de riesgos.","Estándares internacionales de mejores prácticas gestión yde supervisión de riesgos.",
    "Análisis Financiero y Contabilidad a nivel general.",
    "Innovación Financiera, transformación digital, Fintech,Servicios Financieros Digitales."
    "Legislación y marco regulatorio del sistema financiero.",
    "Conocimientos de productos y servicios financieros.","Idiomas Inglés, deseable",
    "Blockchain y Criptomonedas.","Metodología para realizar auditoría de sistemas, supervisión y evaluación de la gestión del riesgo tecnológico.",
    "Estándares internacionales de mejores prácticas gestión y de supervisión de riesgo tecnológico.",
    "Tecnologías de la Información y comunicaciones.",
    "Sistemas de Gestión de la Seguridad de la Información.",
    "Marcos de gestión de Ciberseguridad.",
    "Sistema de Gestión de la Continuidad del Negocio.",
    "Prácticas para desarrollo seguro.",
    "Pruebas de vulnerabilidad y penetración, metodología y herramientas.",
    "Informática forense.","mapas de riesgos","solicitudes de autorización, renovación, modificación de Asientos Registrales de la industria aseguradora."
}

# Función para extraer texto de un archivo PDF o DOCX
def extract_text(file: UploadFile) -> str:
    text = ""
    if file.filename.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file.file)
        text = " ".join(page.extract_text() for page in pdf_reader.pages if page.extract_text())
    elif file.filename.endswith(".docx"):
        text = docx2txt.process(file.file)
    return text.lower()  # Convertir todo a minúsculas para evitar errores de coincidencia

# Función para extraer habilidades del texto
def extract_skills(text: str) -> list:
    return [skill for skill in SKILLS_LIST if skill in text]

# Función para extraer experiencia en años usando expresiones regulares
def extract_experience(text: str) -> list:
    experience = re.findall(r"(\d+)\s*(?:años|years)", text)
    return experience if experience else []

# Función para calcular la similitud semántica entre el CV y la descripción del trabajo
def match_resume_to_job(resume_text: str, job_desc: str) -> float:
    embeddings = model.encode([resume_text, job_desc], convert_to_tensor=True)
    score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
    return round(score, 2)

# Generar un feedback detallado usando GPT-4
def generate_gpt_feedback(resume_text: str, job_desc: str) -> str:
    prompt = f"""
    Analiza el siguiente currículum en comparación con la descripción del trabajo.
    - Resume los puntos fuertes y débiles del candidato.
    - Explica si tiene las habilidades requeridas o no.
    - Da recomendaciones para mejorar su perfil.
    - Que tenga experiencia relacionada a las actividades descritas a la solicitud del empleador.

    --- Currículum ---
    {resume_text}

    --- Descripción del Trabajo ---
    {job_desc}

    Proporciona un análisis claro y detallado.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Eres un experto en selección de talento."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content  # Obtener la respuesta del modelo

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
        "feedback": feedback  # 🆕 Agregado para mejorar la evaluación
    }

    return result

# Verificación de que FastAPI está funcionando en producción
@app.get("/")
def read_root():
    return {"message": "🚀 FastAPI Resume Analyzer está funcionando correctamente en Railway!"}

# Configuración para producción
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000)) 
    uvicorn.run(app, host="0.0.0.0", port=port)
