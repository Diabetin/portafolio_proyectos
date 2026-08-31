from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'tienda/index.html')
def carrito(request):
    return render(request, 'tienda/carrito.html')
def detalle(request):
    return render(request, 'tienda/detalle.html')