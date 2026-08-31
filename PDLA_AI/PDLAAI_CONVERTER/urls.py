from django.urls import path
from . import views

urlpatterns = [
    path('', views.converter_view, name='converter_view'),
]
