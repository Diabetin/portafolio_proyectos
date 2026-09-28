# PDLAAI_DATAEX/views.py
import os
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from .utils import procesar_cv_gemini  # <-- Importamos la función

def extractor_view(request):
    if request.method == 'POST' and request.FILES.get('cv_pdf'):
        pdf_file = request.FILES['cv_pdf']
        fs = FileSystemStorage()
        filename = fs.save(pdf_file.name, pdf_file)
        filepath = os.path.join(settings.MEDIA_ROOT, filename)

        # Usamos la función ayudante para obtener los datos
        datos_diccionario = procesar_cv_gemini(filepath)
        
        return render(request, 'visualizer.html', {
            'extracted_data': datos_diccionario,
            'pdf_url': fs.url(filename)
        })

    return render(request, 'upload.html')

