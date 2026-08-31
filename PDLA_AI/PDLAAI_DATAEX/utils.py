# PDLAAI_DATAEX/utils.py
import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def procesar_cv_gemini(filepath):
    """
    Esta función solo se encarga de hablar con la IA. 
    Recibe la ruta del PDF y devuelve el diccionario de Python.
    """
    document = client.files.upload(file=filepath, config={'display_name': "CV"})

    prompt = """
        Analiza este currículum y devuelve EXCLUSIVAMENTE un JSON válido con esta estructura exacta: 
        {
            "name": "", 
            "email": "", 
            "phone": "", 
            "education": [{"institution": "", "degree": "", "year": ""}], 
            "work_experience": [{"position": "", "company": "", "year": "", "description": ""}],
            "skills": ["habilidad 1", "habilidad 2"],
            "languages": ["idioma 1 con nivel", "idioma 2 con nivel"]
        }
        No incluyas texto adicional ni formato markdown.
        """
    response = client.models.generate_content(
        model='gemini-3.7-flash',
        contents=[document, prompt]
    )
    
    try:
        texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(texto_limpio)
    except json.JSONDecodeError:
        return {"name": "Error leyendo formato"}