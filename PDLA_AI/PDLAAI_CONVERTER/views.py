# Vistas para convertir datos extraidos de PDF con IA en formato JSON a formato LaTeX(.tex)
# PDLAAI_CONVERTER/views.py
import os
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.http import HttpResponse

# Importamos la conexión con Gemini de tu primera app (asegúrate de tener el archivo utils.py creado)
from PDLAAI_DATAEX.utils import procesar_cv_gemini 

def generar_codigo_latex(datos):
    """Toma el diccionario de Python y lo convierte en un string de LaTeX"""
    
    latex = f"\\documentclass[11pt,a4paper,sans]{{moderncv}}\n"
    latex += f"\\moderncvstyle{{classic}}\n"
    latex += f"\\moderncvcolor{{blue}}\n"
    latex += f"\\usepackage[utf8]{{inputenc}}\n"
    latex += f"\\usepackage[scale=0.75]{{geometry}}\n\n"
    
    # Datos personales
    latex += f"\\name{{{datos.get('name', 'Nombre')}}}{{}}\n"
    latex += f"\\email{{{datos.get('email', '')}}}\n"
    latex += f"\\phone[mobile]{{{datos.get('phone', '')}}}\n\n"
    
    latex += "\\begin{document}\n"
    latex += "\\makecvtitle\n\n"
    
    # Experiencia Laboral
    latex += "\\section{Experiencia}\n"
    for exp in datos.get('work_experience', []):
        year = exp.get('year', '')
        pos = exp.get('position', '')
        comp = exp.get('company', '')
        desc = exp.get('description', '')
        latex += f"\\cventry{{{year}}}{{{pos}}}{{{comp}}}{{}}{{}}{{{desc}}}\n"
        
    # Educación
    latex += "\\section{Educación}\n"
    for edu in datos.get('education', []):
        year = edu.get('year', '')
        deg = edu.get('degree', '')
        inst = edu.get('institution', '')
        latex += f"\\cventry{{{year}}}{{{deg}}}{{{inst}}}{{}}{{}}{{}}\n"
        
    # Habilidades e Idiomas
    latex += "\\section{Habilidades e Idiomas}\n"
    habilidades = ", ".join(datos.get('skills', []))
    idiomas = ", ".join(datos.get('languages', []))
    latex += f"\\cvitem{{Habilidades}}{{{habilidades}}}\n"
    latex += f"\\cvitem{{Idiomas}}{{{idiomas}}}\n"
    
    latex += "\\end{document}"
    return latex

def converter_view(request):
    if request.method == 'POST' and request.FILES.get('cv_pdf'):
        pdf_file = request.FILES['cv_pdf']
        fs = FileSystemStorage()
        filename = fs.save(pdf_file.name, pdf_file)
        filepath = os.path.join(settings.MEDIA_ROOT, filename)

        # 1. Extraemos los datos con la IA
        datos_diccionario = procesar_cv_gemini(filepath)
        
        # 2. Generamos el código LaTeX
        codigo_latex = generar_codigo_latex(datos_diccionario)
        
        # Si el usuario hizo clic en "Descargar .tex"
        if 'descargar' in request.POST:
            response = HttpResponse(codigo_latex, content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="curriculum.tex"'
            return response
            
        # 3. Renderizamos la plantilla (Hereda de la app base)
        return render(request, 'converter_visualizer.html', {
            'extracted_data': datos_diccionario,
            'pdf_url': fs.url(filename),
            'codigo_latex': codigo_latex
        })

    return render(request, 'upload_converter.html')
