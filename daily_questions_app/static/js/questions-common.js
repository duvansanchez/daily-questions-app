// Funcionalidad común para todas las plantillas de preguntas
// Aplicando el patrón Strategy para reutilizar código

// Reloj en vivo común
function actualizarReloj() {
    const ahora = new Date();
    const h = String(ahora.getHours()).padStart(2, '0');
    const m = String(ahora.getMinutes()).padStart(2, '0');
    const s = String(ahora.getSeconds()).padStart(2, '0');
    const relojElement = document.getElementById('reloj');
    if (relojElement) {
        relojElement.textContent = `${h}:${m}:${s}`;
    }
}

// Inicializar reloj
function inicializarReloj() {
    setInterval(actualizarReloj, 1000);
    actualizarReloj();
}

// Mostrar preguntas al pulsar el botón (común para todas las plantillas)
function inicializarBotonIniciar() {
    const iniciarBtn = document.getElementById('iniciar-btn');
    if (iniciarBtn) {
        iniciarBtn.addEventListener('click', function() {
            document.getElementById('bienvenida-card').style.display = 'none';
            document.getElementById('preguntas-container').style.display = 'block';
            const header = document.getElementById('bienvenida-header');
            if (header) header.style.display = 'none';
            // Mostrar la primera pregunta
            const cards = document.querySelectorAll('.question-card');
            if (cards.length > 0) {
                cards[0].style.display = 'block';
            }
        });
    }
}

// Inicializar funcionalidad común
function inicializarFuncionalidadComun() {
    inicializarReloj();
    inicializarBotonIniciar();
}

// Auto-inicializar cuando se carga el DOM
document.addEventListener('DOMContentLoaded', inicializarFuncionalidadComun);

// Exportar funciones para uso global
window.inicializarFuncionalidadComun = inicializarFuncionalidadComun;
window.actualizarReloj = actualizarReloj;
window.inicializarReloj = inicializarReloj;
window.inicializarBotonIniciar = inicializarBotonIniciar;