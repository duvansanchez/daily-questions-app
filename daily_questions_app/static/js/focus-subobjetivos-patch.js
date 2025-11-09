// Parche para agregar selects de acciones a los subobjetivos
// Este archivo se ejecuta después de cargar los subobjetivos para agregar los selects

// Variable global para almacenar datos de subobjetivos
window.currentSubobjetivos = [];
let patcheandoSubobjetivos = false;

// Función para agregar selects de acciones a subobjetivos existentes
function agregarBotonesFocusSubobjetivos() {
    if (patcheandoSubobjetivos) {
        console.log('⏳ Parche ya en ejecución, omitiendo...');
        return;
    }
    
    patcheandoSubobjetivos = true;
    console.log('🔧 Aplicando parche para selects de acciones en subobjetivos...');
    
    const container = document.getElementById('focus-subobjetivos-list');
    if (!container) {
        console.log('❌ Container de subobjetivos no encontrado');
        return;
    }
    
    const items = container.querySelectorAll('.focus-subobjetivo-item');
    console.log(`🔍 Encontrados ${items.length} items de subobjetivos`);
    
    items.forEach(item => {
        // Verificar si ya tiene select de acciones
        if (item.querySelector('.focus-subobjetivo-select')) {
            return; // Ya tiene select
        }
        
        const checkbox = item.querySelector('.focus-subobjetivo-checkbox');
        const titulo = item.querySelector('.focus-subobjetivo-titulo');
        
        if (!checkbox || !titulo) {
            console.log('❌ Checkbox o título no encontrado en item');
            return;
        }
        
        const subobjetivoId = checkbox.getAttribute('data-subobjetivo-id');
        const isCompleted = checkbox.checked;
        const tituloTexto = titulo.textContent.trim();
        
        if (!subobjetivoId) {
            console.log('❌ ID de subobjetivo no encontrado');
            return;
        }
        
        // Simplificar estructura - solo agregar el select al final del item
        item.style.display = 'flex';
        item.style.alignItems = 'center';
        item.style.justifyContent = 'space-between';
        
        // Crear select de acciones básico
        const selectAcciones = document.createElement('select');
        selectAcciones.className = 'focus-subobjetivo-select';
        selectAcciones.style.cssText = `
            width: 60px;
            font-size: 14px;
            text-align: center;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 2px;
            background: white;
            margin-left: 8px;
        `;
        
        // Agregar opciones
        const opcionVacia = document.createElement('option');
        opcionVacia.value = '';
        opcionVacia.textContent = '⋯';
        selectAcciones.appendChild(opcionVacia);
        
        const opcionFocus = document.createElement('option');
        opcionFocus.value = 'focus';
        opcionFocus.textContent = '🎯 Focus';
        selectAcciones.appendChild(opcionFocus);
        
        const opcionEditar = document.createElement('option');
        opcionEditar.value = 'editar';
        opcionEditar.textContent = '✏️ Editar';
        selectAcciones.appendChild(opcionEditar);
        
        const opcionEliminar = document.createElement('option');
        opcionEliminar.value = 'eliminar';
        opcionEliminar.textContent = '🗑️ Eliminar';
        selectAcciones.appendChild(opcionEliminar);
        
        // NO deshabilitar el select aunque esté completado
        // Los usuarios deben poder editar/eliminar subobjetivos completados
        
        // Agregar evento al select
        selectAcciones.onchange = function() {
            const accion = this.value;
            console.log('Select cambiado a:', accion);
            
            if (!accion) return;
            
            // Resetear select
            this.value = '';
            
            if (accion === 'focus') {
                console.log('Ejecutando focus para:', subobjetivoId);
                if (typeof abrirModoFocusSubobjetivo === 'function') {
                    abrirModoFocusSubobjetivo(subobjetivoId, tituloTexto);
                } else {
                    alert('Función de focus no disponible');
                }
            } else if (accion === 'editar') {
                console.log('Ejecutando editar para:', subobjetivoId);
                editarSubobjetivoInline(subobjetivoId, titulo);
            } else if (accion === 'eliminar') {
                console.log('Ejecutando eliminar para:', subobjetivoId);
                eliminarSubobjetivoInline(subobjetivoId, item);
            }
        };
        
        // Agregar indicador de tiempo si existe tiempo acumulado
        const subobjetivoData = window.currentSubobjetivos?.find(s => s.id == subobjetivoId);
        if (subobjetivoData && subobjetivoData.tiempo_focus > 0) {
            const minutos = Math.floor(subobjetivoData.tiempo_focus / 60);
            const segundos = subobjetivoData.tiempo_focus % 60;
            const tiempoFormateado = `${minutos}:${segundos.toString().padStart(2, '0')}`;
            
            const tiempoIndicador = document.createElement('small');
            tiempoIndicador.className = 'text-muted ms-2';
            tiempoIndicador.innerHTML = `<i class="bi bi-clock"></i> ${tiempoFormateado}`;
            titulo.appendChild(tiempoIndicador);
        }
        
        // Simplemente agregar el select al final del item
        item.appendChild(selectAcciones);
        
        console.log(`✅ Select de acciones agregado para: ${tituloTexto}`);
    });
    
    patcheandoSubobjetivos = false;
    console.log('🔧 Parche completado');
}

// Función para cargar datos de subobjetivos
async function cargarDatosSubobjetivos() {
    if (!objetivoEnFocus) return;
    
    try {
        const response = await fetch(`/api/objetivos/${objetivoEnFocus.id}/subobjetivos`);
        const subobjetivos = await response.json();
        window.currentSubobjetivos = subobjetivos;
        console.log('📊 Datos de subobjetivos cargados:', subobjetivos.length);
    } catch (error) {
        console.error('Error cargando datos de subobjetivos:', error);
    }
}

// Observar cambios en el container de subobjetivos
function observarCambiosSubobjetivos() {
    const container = document.getElementById('focus-subobjetivos-list');
    if (!container) {
        console.log('❌ Container de subobjetivos no encontrado para observar');
        return;
    }
    
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                console.log('🔄 Cambios detectados en subobjetivos, aplicando parche...');
                setTimeout(async () => {
                    await cargarDatosSubobjetivos();
                    agregarBotonesFocusSubobjetivos();
                }, 100);
            }
        });
    });
    
    observer.observe(container, {
        childList: true,
        subtree: true
    });
    
    console.log('👁️ Observer configurado para subobjetivos');
}

// Inicializar cuando se abra el modal de focus
document.addEventListener('DOMContentLoaded', function() {
    const modalFocus = document.getElementById('modalFocusObjetivo');
    if (modalFocus) {
        modalFocus.addEventListener('shown.bs.modal', function() {
            console.log('🎯 Modal de focus abierto, configurando observer...');
            setTimeout(() => {
                observarCambiosSubobjetivos();
                agregarBotonesFocusSubobjetivos();
            }, 500);
        });
    }
});

// También intentar aplicar el parche inmediatamente si ya hay subobjetivos
setTimeout(() => {
    agregarBotonesFocusSubobjetivos();
    observarCambiosSubobjetivos();
}, 1000);

// Función para editar subobjetivo inline
function editarSubobjetivoInline(subobjetivoId, tituloElement) {
    // Obtener solo el texto del título, sin elementos hijos (como el tiempo)
    let textoOriginal = '';
    for (let node of tituloElement.childNodes) {
        if (node.nodeType === Node.TEXT_NODE) {
            textoOriginal += node.textContent;
        }
    }
    
    // Limpiar cualquier formato de tiempo que pueda quedar
    textoOriginal = textoOriginal.trim()
        .replace(/\s*\(\d{1,3}:\d{2}\)\s*$/, '')  // (123:45)
        .replace(/\s*\(\d{1,3}:\d{2}:\d{2}\)\s*$/, '')  // (1:23:45)
        .replace(/\s*-\s*\d{1,3}:\d{2}\s*$/, '')  // - 123:45
        .replace(/\s*\[\d{1,3}:\d{2}\]\s*$/, '')  // [123:45]
        .replace(/\s*\d{1,3}:\d{2}\s*$/, '')      // 123:45
        .replace(/\s*⏱️.*$/, '')                   // ⏱️ cualquier cosa
        .replace(/\s*🕐.*$/, '')                   // 🕐 cualquier cosa
        .trim();
    
    // Crear input que se adapte al espacio disponible
    const input = document.createElement('input');
    input.type = 'text';
    input.value = textoOriginal;
    input.style.cssText = `
        width: 100%;
        max-width: none;
        flex: 1;
        padding: 4px 8px;
        border: 2px solid #007bff;
        border-radius: 4px;
        font-size: 14px;
        background: white;
        outline: none;
        box-sizing: border-box;
        margin: 0;
    `;
    
    // Guardar referencia al elemento original
    const elementoOriginal = tituloElement;
    
    // Reemplazar título con input
    tituloElement.parentNode.replaceChild(input, tituloElement);
    input.focus();
    input.select();
    
    // Función para restaurar
    function restaurar() {
        if (!input.parentNode) return; // Ya fue removido
        
        const nuevoSpan = document.createElement('span');
        nuevoSpan.className = 'focus-subobjetivo-titulo';
        nuevoSpan.textContent = textoOriginal;
        
        // Restaurar indicador de tiempo si existía
        const subobjetivoData = window.currentSubobjetivos?.find(s => s.id == subobjetivoId);
        if (subobjetivoData && subobjetivoData.tiempo_focus > 0) {
            const minutos = Math.floor(subobjetivoData.tiempo_focus / 60);
            const segundos = subobjetivoData.tiempo_focus % 60;
            const tiempoFormateado = `${minutos}:${segundos.toString().padStart(2, '0')}`;
            
            const tiempoIndicador = document.createElement('small');
            tiempoIndicador.className = 'text-muted ms-2';
            tiempoIndicador.innerHTML = `<i class="bi bi-clock"></i> ${tiempoFormateado}`;
            nuevoSpan.appendChild(tiempoIndicador);
        }
        
        input.parentNode.replaceChild(nuevoSpan, input);
    }
    
    // Guardar con Enter
    input.addEventListener('keypress', async function(e) {
        if (e.key === 'Enter') {
            const nuevoTexto = input.value.trim();
            if (nuevoTexto && nuevoTexto !== textoOriginal) {
                try {
                    const response = await fetch(`/api/subobjetivos/${subobjetivoId}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ titulo: nuevoTexto })
                    });
                    
                    if (response.ok) {
                        if (!input.parentNode) return; // Ya fue removido
                        
                        const nuevoSpan = document.createElement('span');
                        nuevoSpan.className = 'focus-subobjetivo-titulo';
                        nuevoSpan.textContent = nuevoTexto;
                        
                        // Restaurar indicador de tiempo si existía
                        const subobjetivoData = window.currentSubobjetivos?.find(s => s.id == subobjetivoId);
                        if (subobjetivoData && subobjetivoData.tiempo_focus > 0) {
                            const minutos = Math.floor(subobjetivoData.tiempo_focus / 60);
                            const segundos = subobjetivoData.tiempo_focus % 60;
                            const tiempoFormateado = `${minutos}:${segundos.toString().padStart(2, '0')}`;
                            
                            const tiempoIndicador = document.createElement('small');
                            tiempoIndicador.className = 'text-muted ms-2';
                            tiempoIndicador.innerHTML = `<i class="bi bi-clock"></i> ${tiempoFormateado}`;
                            nuevoSpan.appendChild(tiempoIndicador);
                        }
                        
                        input.parentNode.replaceChild(nuevoSpan, input);
                        console.log('✅ Subobjetivo actualizado correctamente');
                    } else {
                        alert('Error al actualizar');
                        restaurar();
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                    restaurar();
                }
            } else {
                restaurar();
            }
        } else if (e.key === 'Escape') {
            restaurar();
        }
    });
    
    // Solo cancelar con Escape, no con blur para evitar que se cierre inmediatamente
}

// Función para eliminar subobjetivo
async function eliminarSubobjetivoInline(subobjetivoId, itemElement) {
    // Usar SweetAlert2 para confirmación
    const result = await Swal.fire({
        title: '¿Eliminar subobjetivo?',
        text: 'Esta acción no se puede deshacer',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar'
    });
    
    if (!result.isConfirmed) return;
    
    try {
        const response = await fetch(`/api/subobjetivos/${subobjetivoId}`, { 
            method: 'DELETE' 
        });
        
        if (response.ok) {
            itemElement.remove();
            
            // Actualizar contador
            setTimeout(() => {
                const container = document.getElementById('focus-subobjetivos-list');
                const total = container.querySelectorAll('input[type="checkbox"]').length;
                const completados = container.querySelectorAll('input[type="checkbox"]:checked').length;
                const progreso = document.getElementById('focus-progreso');
                if (progreso) {
                    progreso.textContent = `${completados}/${total}`;
                }
            }, 100);
            
            // Mostrar mensaje de éxito
            Swal.fire({
                title: '¡Eliminado!',
                text: 'El subobjetivo ha sido eliminado correctamente',
                icon: 'success',
                timer: 2000,
                showConfirmButton: false
            });
            
        } else {
            Swal.fire({
                title: 'Error',
                text: 'Error al eliminar del servidor',
                icon: 'error'
            });
        }
    } catch (error) {
        Swal.fire({
            title: 'Error de conexión',
            text: 'No se pudo conectar con el servidor: ' + error.message,
            icon: 'error'
        });
    }
}