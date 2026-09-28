# Archivo: F:\PDLA_AI\PDLA_DATAEX\urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Cuando alguien entre a /upload/, Django ejecutará 'extractor_view'
    path('upload/', views.extractor_view, name='extractor_view'),
]