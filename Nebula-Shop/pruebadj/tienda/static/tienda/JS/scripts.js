// Inicializar AOS
AOS.init({
    duration: 1000,
    once: true,
    offset: 100
});

// Productos
const productos = [
    {
        id: 1,
        nombre: "Nave X-1 Interceptor",
        precio: 299900,
        imagen: "https://im.ziffdavisinternational.com/ign_es/screenshot/default/normandysr2b_29eu.jpg",
        descripcion: "Nave ligera para misiones rápidas. Velocidad máxima: 0.9c",
        detallesLargos: "La X-1 Interceptor está diseñada para misiones tácticas de alta velocidad dentro del sistema solar. Cabina para 1 piloto, motor de curvatura ligera y blindaje de carbono reforzado."
    },
    {
        id: 2,
        nombre: "Crucero Nova Prime",
        precio: 1250000,
        imagen: "https://fotografias-neox.atresmedia.com/clipping/cmsimages01/2016/04/15/979CC3AE-529D-454E-B0DB-28E2734F8F11/97.jpg?crop=1920,1080,x0,y0&width=1600&height=900&optimize=high&format=webply",
        descripcion: "Nave familiar con capacidad para 12 tripulantes. Ideal para colonización.",
        detallesLargos: "El Crucero Nova Prime incluye dormitorios modulares, sistema de soporte vital de larga duración y hangar para 2 naves auxiliares. Perfecto para colonias en expansión."
    },
    {
        id: 3,
        nombre: "Destructor Orion",
        precio: 4500000,
        imagen: "https://i.blogs.es/e8f854/c8724475-496f-46d2-9f97-3a13d08e778c/1366_2000.jpg",
        descripcion: "Potencia de fuego impresionante. Perfecta para defensa planetaria.",
        detallesLargos: "El Destructor Orion cuenta con cañones de iones, escudos deflectores de última generación y sistema de radares de alcance interplanetario."
    },
    {
        id: 4,
        nombre: "Explorador Zeta",
        precio: 850000,
        imagen: "https://cinepremiere.com.mx/assets/images/Blogs/LadoObscuroSala/2013/Agostodieciseisonce.jpg",
        descripcion: "Diseñada para exploración profunda. Sensores de última generación.",
        detallesLargos: "Explorador de largo alcance equipado con laboratorio científico, drones de reconocimiento y sensores de materia oscura."
    }
];

// Carrito en localStorage
let carrito = JSON.parse(localStorage.getItem('carrito')) || [];

// Render productos (grilla Bootstrap)
function renderizarProductos() {
    const $container = $('#productos-container');
    if (!$container.length) return;

    $container.empty();
    productos.forEach(producto => {
        const card = `
            <div class="col-12 col-sm-6 col-lg-3" data-aos="fade-up" data-aos-delay="${producto.id * 100}">
                <article class="card product-card h-100 text-center">
                    <img src="${producto.imagen}" class="card-img-top" alt="${producto.nombre}"
                         style="height: 200px; object-fit: cover;">
                    <div class="card-body d-flex flex-column">
                        <h5 class="card-title">${producto.nombre}</h5>
                        <p class="card-text">${producto.descripcion}</p>
                        <p class="text-success fw-bold fs-5 mb-3">$${producto.precio.toLocaleString()}</p>
                        <div class="mt-auto d-grid gap-2">
                            <button class="btn btn-primary agregar-carrito" data-id="${producto.id}">
                                Agregar al Carrito 🚀
                            </button>
                            <a href="${window.DETALLE_URL}?id=${producto.id}" class="btn btn-outline-light">
                                Ver más
                            </a>
                        </div>
                    </div>
                </article>
            </div>
        `;
        $container.append(card);
    });
}

// Badge carrito
function actualizarContadorCarrito() {
    const totalItems = carrito.reduce((sum, item) => sum + item.cantidad, 0);
    const badge = document.querySelector('#cart-count');
    if (!badge) return;

    badge.textContent = totalItems;
    if (totalItems > 0) badge.classList.add('animate__pulse');
    else badge.classList.remove('animate__pulse');
}

// Dropdown carrito
function renderizarDropdownCarrito() {
    const container = $('#dropdown-carrito');
    if (!container.length) return;

    const totalItems = carrito.reduce((sum, item) => sum + item.cantidad, 0);
    const totalPrecio = carrito.reduce((sum, item) => sum + (item.precio * item.cantidad), 0);
    
    if (totalItems === 0) {
        container.html(`
            <li>
                <div class="dropdown-item text-center py-3">
                    <h6 class="text-muted mb-1">Carrito vacío</h6>
                    <p class="mb-0 small">¡Añade productos!</p>
                </div>
            </li>
        `);
        return;
    }

    let html = `
        <li class="dropdown-header">
            <div class="d-flex justify-content-between align-items-center">
                <span>Tu carrito</span>
                <span class="badge bg-primary">${totalItems}</span>
            </div>
        </li>
    `;
    
    carrito.forEach(item => {
        html += `
            <li>
                <div class="dropdown-item p-2">
                    <div class="row align-items-center g-2">
                        <div class="col-3">
                            <img src="${item.imagen}" class="img-fluid rounded"
                                 style="width: 50px; height: 40px; object-fit: cover;">
                        </div>
                        <div class="col-6">
                            <h6 class="mb-0 small">${item.nombre}</h6>
                            <small class="text-success">$${item.precio.toLocaleString()}</small>
                        </div>
                        <div class="col-3 text-end">
                            <span class="badge bg-primary small">${item.cantidad}</span>
                        </div>
                    </div>
                </div>
            </li>
        `;
    });
    
    html += `
        <li><hr class="dropdown-divider"></li>
        <li>
            <div class="dropdown-item text-end p-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span>Total:</span>
                    <strong>$${totalPrecio.toLocaleString()}</strong>
                </div>
            </div>
        </li>
        <li><hr class="dropdown-divider"></li>
        <li>
            <a class="dropdown-item text-center py-2" href="${window.CARRITO_URL}">
                <strong>Ver carrito completo →</strong>
            </a>
        </li>
    `;
    
    container.html(html);
}

// Carrito completo
function renderizarCarrito() {
    const container = $('#carrito-container');
    if (!container.length) return;

    const total = carrito.reduce((sum, item) => sum + (item.precio * item.cantidad), 0);
    
    if (carrito.length === 0) {
        container.html(`
            <div class="text-center py-5">
                <div class="animate__animated animate__bounceIn">
                    <h5 class="text-muted">Tu carrito está vacío</h5>
                    <p>¡Añade productos desde la página de productos!</p>
                </div>
            </div>
        `);
        const totalSpan = document.querySelector('#total-price');
        if (totalSpan) totalSpan.textContent = '0';
        return;
    }

    let html = '<div class="row g-3">';
    carrito.forEach(item => {
        html += `
            <div class="col-12">
                <article class="card bg-dark text-white">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-4 col-md-3">
                                <img src="${item.imagen}" class="img-fluid rounded" alt="${item.nombre}">
                            </div>
                            <div class="col-8 col-md-6">
                                <h6>${item.nombre}</h6>
                                <p class="mb-1">$${item.precio.toLocaleString()}</p>
                            </div>
                            <div class="col-12 col-md-3 text-end mt-2 mt-md-0">
                                <div class="input-group input-group-sm mb-1">
                                    <button class="btn btn-outline-secondary decrementar" data-id="${item.id}">-</button>
                                    <input type="number" class="form-control text-center" value="${item.cantidad}" readonly>
                                    <button class="btn btn-outline-secondary incrementar" data-id="${item.id}">+</button>
                                </div>
                                <button class="btn btn-sm btn-outline-danger eliminar-item" data-id="${item.id}">
                                    Eliminar
                                </button>
                            </div>
                        </div>
                    </div>
                </article>
            </div>
        `;
    });
    html += '</div>';
    
    container.html(html);
    const totalSpan = document.querySelector('#total-price');
    if (totalSpan) totalSpan.textContent = total.toLocaleString();
}

// Detalle de producto
function renderizarDetalleProducto() {
    const container = $('#detalle-producto');
    if (!container.length) return;

    const params = new URLSearchParams(window.location.search);
    const id = parseInt(params.get('id'));
    const producto = productos.find(p => p.id === id);

    if (!producto) {
        container.html(`
            <div class="col-12 text-center py-5">
                <h3 class="mb-3">Producto no encontrado</h3>
                <a href="${window.INDEX_URL}#productos" class="btn btn-primary">Volver a productos</a>
            </div>
        `);
        return;
    }

    container.html(`
        <div class="col-12 col-lg-6" data-aos="fade-right">
            <img src="${producto.imagen}" alt="${producto.nombre}" class="img-fluid rounded shadow">
        </div>
        <div class="col-12 col-lg-6" data-aos="fade-left">
            <h1 class="mb-3">${producto.nombre}</h1>
            <p class="lead">${producto.descripcion}</p>
            <p>${producto.detallesLargos}</p>
            <h3 class="text-success fw-bold mb-4">$${producto.precio.toLocaleString()}</h3>
            <div class="d-flex flex-wrap gap-2">
                <button class="btn btn-primary agregar-carrito" data-id="${producto.id}">
                    Agregar al Carrito 🚀
                </button>
                <a href="${window.INDEX_URL}#productos" class="btn btn-outline-light">
                    Volver a productos
                </a>
            </div>
        </div>
    `);
}

// Eventos
$(document).ready(function() {
    // Scroll suave anclas
    $('a[href^="#"]').on('click', function(e) {
        const href = $(this).attr('href');
        if (href.startsWith('#') && href.length > 1) {
            e.preventDefault();
            const target = $(href);
            if (target.length) {
                $('html, body').animate({
                    scrollTop: target.offset().top - 80
                }, 800);
            }
        }
    });

    // Render inicial
    renderizarProductos();
    renderizarDetalleProducto();
    renderizarCarrito();
    actualizarContadorCarrito();
    renderizarDropdownCarrito();

    // Agregar carrito
    $(document).on('click', '.agregar-carrito', function() {
        const id = parseInt($(this).data('id'));
        const producto = productos.find(p => p.id === id);
        
        const itemExistente = carrito.find(item => item.id === id);
        if (itemExistente) itemExistente.cantidad++;
        else carrito.push({ ...producto, cantidad: 1 });
        
        localStorage.setItem('carrito', JSON.stringify(carrito));
        actualizarContadorCarrito();
        renderizarDropdownCarrito();
        renderizarCarrito();
        
        $(this)
            .addClass('animate__animated animate__tada')
            .delay(500)
            .queue(function() {
                $(this).removeClass('animate__tada').dequeue();
            });
    });

    // Incrementar / Decrementar / Eliminar
    $(document).on('click', '.incrementar', function() {
        const id = parseInt($(this).data('id'));
        const item = carrito.find(item => item.id === id);
        if (item) item.cantidad++;
        localStorage.setItem('carrito', JSON.stringify(carrito));
        renderizarCarrito();
        renderizarDropdownCarrito();
        actualizarContadorCarrito();
    });

    $(document).on('click', '.decrementar', function() {
        const id = parseInt($(this).data('id'));
        const item = carrito.find(item => item.id === id);
        if (item) {
            item.cantidad--;
            if (item.cantidad <= 0) carrito = carrito.filter(i => i.id !== id);
        }
        localStorage.setItem('carrito', JSON.stringify(carrito));
        renderizarCarrito();
        renderizarDropdownCarrito();
        actualizarContadorCarrito();
    });

    $(document).on('click', '.eliminar-item', function() {
        const id = parseInt($(this).data('id'));
        carrito = carrito.filter(item => item.id !== id);
        localStorage.setItem('carrito', JSON.stringify(carrito));
        renderizarCarrito();
        renderizarDropdownCarrito();
        actualizarContadorCarrito();
    });

    const btnVaciar = document.querySelector('#vaciar-carrito');
    if (btnVaciar) {
        btnVaciar.addEventListener('click', () => {
            carrito = [];
            localStorage.setItem('carrito', JSON.stringify(carrito));
            renderizarCarrito();
            renderizarDropdownCarrito();
            actualizarContadorCarrito();
        });
    }

    // Fondo espacial con jQuery Starfield en todas las páginas
    if ($('#space-bg').length && typeof $.fn.starfield === 'function') {
        $('#space-bg').starfield({
            starDensity: 1.5,
            mouseScale: 0.5,
            seedMovement: true
        });
    }
        // ========================
    // Nave espacial aleatoria
    // ========================
    function lanzarNaveAleatoria() {
        const $ship = $('#spaceship');
        if (!$ship.length) return;

        const anchoVentana = $(window).width();
        const altoVentana  = $(window).height();

        // Altura aleatoria entre 10% y 80% de la pantalla
        const topRandom = (Math.random() * 70 + 10); // %
        // Dirección aleatoria: 0 = izquierda→derecha, 1 = derecha→izquierda
        const direccion = Math.random() < 0.5 ? 'left-right' : 'right-left';
        // Duración aleatoria entre 8 y 14 segundos
        const duracion = (Math.random() * 6000) + 8000;

        if (direccion === 'left-right') {
            $ship.removeClass('flip'); // mira hacia la derecha
            $ship
                .stop(true, true)
                .css({
                    top: topRandom + 'vh',
                    left: -100
                })
                .animate(
                    { left: anchoVentana + 100 },
                    duracion,
                    'linear',
                    function() {
                        $(this).css('left', -100);
                    }
                );
        } else {
            $ship.addClass('flip'); // mira hacia la izquierda
            $ship
                .stop(true, true)
                .css({
                    top: topRandom + 'vh',
                    left: anchoVentana + 100
                })
                .animate(
                    { left: -100 },
                    duracion,
                    'linear',
                    function() {
                        $(this).css('left', anchoVentana + 100);
                    }
                );
        }
    }

    // Lanzar primera vez al cargar
    lanzarNaveAleatoria();
    // Volar de nuevo cada 15–25 segundos de forma aleatoria
    setInterval(function() {
        lanzarNaveAleatoria();
    }, Math.floor(Math.random() * 10000) + 15000);

});
