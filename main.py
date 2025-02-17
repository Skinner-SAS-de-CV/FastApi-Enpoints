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
load_dotenv(override=True)

# Verificar que la API Key de OpenAI está configurada
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("⚠️ ERROR: La API Key de OpenAI no se encontró. Verifica tu archivo .env o las variables de entorno en Railway.")

client = OpenAI(api_key=OPENAI_API_KEY)

print("🔍 API Key cargada en el backend:", os.getenv("OPENAI_API_KEY"))

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
    "administración de empresas", "economista", "auditor", "gestión de personas",
    "liderazgo de ventas", "trabajo en equipo", "resolución de problemas", "toma de decisiones",
    "adaptación al cambio", "comunicación efectiva", "proactividad", "empatía",
    "creatividad", "tolerancia a la presión", "orientación a resultados",
    "compromiso", "capacidad de aprendizaje", "innovación", "resolución de conflictos",
    "Metodología para auditoría y supervisión basada en riesgos.",
    "Gestión y medición de riesgos.","Estándares internacionales de supervisión de riesgos.",
    "Análisis Financiero y Contabilidad a nivel general.",
    "Innovación Financiera","Legislación y marco regulatorio del sistema financiero.",
    "Conocimientos de productos y servicios financieros.", "Idiomas Inglés, deseable",
    "Seguridad de la Información.","Continuidad del Negocio.",
     "Mapas de riesgos.", "Gestión de la industria aseguradora."
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
    - Analiza si cumple con el perfil requerido para el puesto.

    --- Currículum ---
    {resume_text}

    --- Descripción del Trabajo ---
            Preparar las solicitudes de opiniones técnicas.
        Elaborar informes ejecutivos de resultados relevantes de la supervisión.
        Elaborar diagnósticos y planes de trabajo de los procesos de supervisión.
        Realizar visitas de supervisión con un enfoque basado en riesgos dando cumplimiento de
        la normativa por parte de las entidades supervisadas, tomando en cuenta las mejores
        prácticas y estándares internacionales y los servicios que las entidades hayan
        tercerizado para mitigar cualquier deterioro de calidad.
        Efectuar visitas de supervisión focalizadas, ampliadas y de cumplimiento de acuerdo con
        el plan operativo.
        Preparar programas de trabajo conforme actividades asignadas por el Coordinador de
        Visita de Supervisión o el Jefe de Departamento.
        Efectuar análisis técnicos y monitoreos requeridos por la administración superior.
        Efectuar monitoreos periódicos de cumplimientos legales y normativos.
        Desarrollar exámenes de auditoría de diversa índole durante las actividades de
        supervisión realizadas en las entidades supervisadas.
        Evaluar la gestión de riesgos desarrolladas por las entidades supervisadas
        Documentar los presuntos incumplimientos determinados en las evaluaciones de
        auditoría y participar en la elaboración del informe correspondiente.
        Elaborar informe parcial de resultados de la visita de supervisión.
        Realizar propuesta de informe para la solicitud de inicio del proceso administrativo
        sancionador por señalamiento de presuntos incumplimientos como resultado de las
        auditorías.
        Elaborar informes de procesos administrativos sancionatorios derivados de presuntos
        incumplimientos legales o normativos determinados en las visitas de supervisión.
        Responder a los requerimientos del departamento de trámites para atender las
        solicitudes de trámites presentados por los supervisados, cuando sea necesario.
        Realizar monitoreos continuos de noticias o denuncias que señalen malas prácticas de
        las entidades supervisadas e informar al jefe inmediato para la activación de visitas de
        supervisión.
        Realizar auditorías hacia los auditores internos y externos responsables de las auditorías
        de las entidades supervisadas.
        Realizar visitas de supervisión para verificar la adecuada implementación de
        modificaciones a leyes y normas así como nuevo marco legal y normativo.
        Atender y canalizar adecuadamente las consultas y solicitudes de apoyo técnico de las
        entidades supervisadas.
        Preparar insumos para los colegios de supervisores y mapas de riesgos.
        Realizar y ejecutar revisiones especiales orientadas a evaluar temas particulares en los
        supervisados, que surjan de alertas generadas por áreas de apoyo.
        Elaborar diagnósticos y planes de trabajo de auditoría.
        Realizar seguimiento a los descargos de las observaciones e incumplimientos
        comunicados a las entidades.
        Discutir durante la ejecución de las visitas de supervisión, las observaciones resultantes
        de las actividades de supervisión con los técnicos de las entidades, cuando aplique.  
        Contribuir en la generación de los insumos para los mapas de riesgos de las entidades
        supervisadas.
        Asistir a Juntas Generales Ordinarias y Extraordinarias de Accionistas de entidades
        supervisadas para obtener información relevante. 
        Realizar monitoreos a la calidad de los servicios tercerizados por las entidades
        supervisadas.
    {job_desc}

    Proporciona un análisis claro y detallado.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Eres un experto en selección de talento humano, planes de carrera, planes de sucesion, analisis de salarios y encuestas de clima organizacional."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content  # Obtener la respuesta del modelo

# Endpoint para analizar un currículum
@app.post("/analyze/")
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
        "decision": "Seleccionado" if match_score > 0.7 else "No fue seleccionado",
        "reason": "Buen perfil" if match_score > 0.7 else "Falta de experiencia o habilidades relevantes",
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
