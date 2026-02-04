// Parche para agregar selects de acciones a los subobjetivos
// Este archivo se ejecuta después de cargar los subobjetivos para agregar los selects

console.log('🔧 Cargando focus-subobjetivos-patch.js...');

// Verificar dependencias al cargar
document.addEventListener('DOMContentLoaded', function() {
    console.log('📋 Verificando dependencias del patch...');
    console.log('- abrirModoFocusSubobjetivo:', typeof abrirModoFocusSubobjetivo);
    console.log('- window.abrirModoFocusSubobjetivo:', typeof window.abrirModoFocusSubobjetivo);
    console.log('- Scripts cargados:', Array.from(document.scripts).map(s => s.src.split('/').pop()).filter(s => s.includes('focus')));
});

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
        
        const opcionSubir = document.createElement('option');
        opcionSubir.value = 'subir';
        opcionSubir.textContent = '⬆️ Subir';
        
        // Deshabilitar si es el primer elemento O si es completado y el anterior no está completado
        const esElPrimero = items[0] === item;
        let deshabilitarSubir = esElPrimero;
        
        if (!esElPrimero && isCompleted) {
            // Si está completado, verificar si el anterior no está completado
            const itemAnterior = items[Array.from(items).indexOf(item) - 1];
            const checkboxAnterior = itemAnterior?.querySelector('.focus-subobjetivo-checkbox');
            if (checkboxAnterior && !checkboxAnterior.checked) {
                deshabilitarSubir = true;
            }
        }
        
        if (deshabilitarSubir) {
            opcionSubir.disabled = true;
            opcionSubir.textContent = '⬆️ Subir (no disponible)';
        }
        selectAcciones.appendChild(opcionSubir);
        
        const opcionBajar = document.createElement('option');
        opcionBajar.value = 'bajar';
        opcionBajar.textContent = '⬇️ Bajar';
        
        // Deshabilitar si es el último elemento O si no está completado y el siguiente está completado
        const esElUltimo = items[items.length - 1] === item;
        let deshabilitarBajar = esElUltimo;
        
        if (!esElUltimo && !isCompleted) {
            // Si no está completado, verificar si el siguiente está completado
            const itemSiguiente = items[Array.from(items).indexOf(item) + 1];
            const checkboxSiguiente = itemSiguiente?.querySelector('.focus-subobjetivo-checkbox');
            if (checkboxSiguiente && checkboxSiguiente.checked) {
                deshabilitarBajar = true;
            }
        }
        
        if (deshabilitarBajar) {
            opcionBajar.disabled = true;
            opcionBajar.textContent = '⬇️ Bajar (no disponible)';
        }
        selectAcciones.appendChild(opcionBajar);
        
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
                console.log('🔍 Verificando disponibilidad de función...');
                console.log('- typeof abrirModoFocusSubobjetivo:', typeof abrirModoFocusSubobjetivo);
                console.log('- typeof window.abrirModoFocusSubobjetivo:', typeof window.abrirModoFocusSubobjetivo);
                
                // Función para ejecutar el focus
                const ejecutarFocus = () => {
                    if (typeof abrirModoFocusSubobjetivo === 'function') {
                        console.log('✅ Usando función directa');
                        abrirModoFocusSubobjetivo(subobjetivoId, tituloTexto);
                        return true;
                    } else if (typeof window.abrirModoFocusSubobjetivo === 'function') {
                        console.log('✅ Usando función de window');
                        window.abrirModoFocusSubobjetivo(subobjetivoId, tituloTexto);
                        return true;
                    }
                    return false;
                };
                
                // Intentar ejecutar inmediatamente
                if (ejecutarFocus()) {
                    return;
                }
                
                // Si no funciona, intentar cargar el script manualmente
                console.log('⚠️ Función no encontrada, intentando cargar script...');
                
                // Verificar si el script está cargado
                const scriptExists = document.querySelector('script[src*="focus-subobjetivos.js"]');
                console.log('📜 Script focus-subobjetivos.js encontrado:', !!scriptExists);
                
                if (!scriptExists) {
                    console.log('🔄 Cargando script manualmente...');
                    const script = document.createElement('script');
                    script.src = '/static/js/focus-subobjetivos.js';
                    script.onload = () => {
                        console.log('✅ Script cargado, reintentando...');
                        setTimeout(() => {
                            if (!ejecutarFocus()) {
                                console.error('❌ Función sigue no disponible después de cargar script');
                                alert('Error: No se pudo cargar la función de focus. Recarga la página.');
                            }
                        }, 100);
                    };
                    script.onerror = () => {
                        console.error('❌ Error cargando script');
                        alert('Error: No se pudo cargar el script de focus. Verifica la conexión.');
                    };
                    document.head.appendChild(script);
                } else {
                    // El script existe pero la función no está disponible
                    console.log('⏳ Script existe, esperando carga completa...');
                    let intentos = 0;
                    const maxIntentos = 10;
                    
                    const verificarFuncion = () => {
                        intentos++;
                        console.log(`🔄 Intento ${intentos}/${maxIntentos}`);
                        
                        if (ejecutarFocus()) {
                            console.log('✅ Función encontrada después de esperar');
                            return;
                        }
                        
                        if (intentos < maxIntentos) {
                            setTimeout(verificarFuncion, 200);
                        } else {
                            console.error('❌ Función no disponible después de múltiples intentos');
                            console.log('🔍 Estado final:');
                            console.log('- window keys:', Object.keys(window).filter(k => k.includes('abrir')));
                            console.log('- scripts cargados:', Array.from(document.scripts).map(s => s.src));
                            alert('Error: Función de focus no disponible después de múltiples intentos. Recarga la página.');
                        }
                    };
                    
                    verificarFuncion();
                }
            } else if (accion === 'subir') {
                console.log('Ejecutando subir para:', subobjetivoId);
                moverSubobjetivoFocus(subobjetivoId, 'arriba');
            } else if (accion === 'bajar') {
                console.log('Ejecutando bajar para:', subobjetivoId);
                moverSubobjetivoFocus(subobjetivoId, 'abajo');
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

// Función para mover subobjetivos en el modo focus
async function moverSubobjetivoFocus(subobjetivoId, direccion) {
    if (!objetivoEnFocus) {
        console.error('No hay objetivo en focus');
        return;
    }
    
    console.log(`🔄 Iniciando movimiento ${direccion} para subobjetivo ${subobjetivoId}`);
    
    try {
        // Obtener la lista actual de subobjetivos
        const response = await fetch(`/api/objetivos/${objetivoEnFocus.id}/subobjetivos`);
        const subobjetivos = await response.json();
        
        console.log('📋 Subobjetivos actuales:', subobjetivos.map(s => `${s.id}: ${s.titulo}`));
        
        // Encontrar el índice del subobjetivo a mover
        const idx = subobjetivos.findIndex(s => s.id == subobjetivoId);
        
        if (idx === -1) {
            console.error('Subobjetivo no encontrado');
            return;
        }
        
        console.log(`📍 Subobjetivo encontrado en posición ${idx}`);
        
        // Verificar si el movimiento es válido considerando el estado de completado
        const subobjetivoActual = subobjetivos[idx];
        
        if (direccion === 'arriba') {
            if (idx === 0) {
                console.log('El subobjetivo ya está en la primera posición');
                return;
            }
            
            // Si el subobjetivo actual está completado, no puede subir por encima de uno no completado
            const subobjetivoArriba = subobjetivos[idx - 1];
            if (subobjetivoActual.completado && !subobjetivoArriba.completado) {
                console.log('Un subobjetivo completado no puede moverse por encima de uno no completado');
                if (typeof showError === 'function') {
                    showError('Los subobjetivos completados deben permanecer al final');
                }
                return;
            }
        }
        
        if (direccion === 'abajo') {
            if (idx === subobjetivos.length - 1) {
                console.log('El subobjetivo ya está en la última posición');
                return;
            }
            
            // Si el subobjetivo actual no está completado, no puede bajar por debajo de uno completado
            const subobjetivoAbajo = subobjetivos[idx + 1];
            if (!subobjetivoActual.completado && subobjetivoAbajo.completado) {
                console.log('Un subobjetivo no completado no puede moverse por debajo de uno completado');
                if (typeof showError === 'function') {
                    showError('Los subobjetivos no completados deben permanecer arriba');
                }
                return;
            }
        }
        
        // Realizar el intercambio
        if (direccion === 'arriba') {
            [subobjetivos[idx - 1], subobjetivos[idx]] = [subobjetivos[idx], subobjetivos[idx - 1]];
            console.log(`🔄 Intercambiando posición ${idx} con ${idx - 1}`);
        } else if (direccion === 'abajo') {
            [subobjetivos[idx], subobjetivos[idx + 1]] = [subobjetivos[idx + 1], subobjetivos[idx]];
            console.log(`🔄 Intercambiando posición ${idx} con ${idx + 1}`);
        }
        
        // Enviar el nuevo orden al servidor
        const ids = subobjetivos.map(s => s.id);
        console.log('📤 Enviando nuevo orden:', ids);
        
        const reorderResponse = await fetch(`/api/objetivos/${objetivoEnFocus.id}/subobjetivos/reordenar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids })
        });
        
        if (reorderResponse.ok) {
            console.log('✅ Orden actualizado correctamente en el servidor');
            
            // Intentar múltiples métodos de recarga para asegurar que funcione
            let recargaExitosa = false;
            
            // Método 1: Función oficial de recarga
            if (typeof recargarSubobjetivosFocus === 'function') {
                console.log('🔄 Método 1: Usando función oficial recargarSubobjetivosFocus...');
                try {
                    await recargarSubobjetivosFocus();
                    recargaExitosa = true;
                    console.log('✅ Recarga exitosa con método 1');
                } catch (error) {
                    console.error('❌ Error en método 1:', error);
                }
            }
            
            // Método 2: Función de renderizado directo
            if (!recargaExitosa && typeof renderizarSubobjetivosFocusCompleto === 'function') {
                console.log('🔄 Método 2: Usando renderizarSubobjetivosFocusCompleto...');
                try {
                    // Obtener datos actualizados
                    const responseActualizada = await fetch(`/api/objetivos/${objetivoEnFocus.id}/subobjetivos`);
                    const subobjetivosActualizados = await responseActualizada.json();
                    
                    // Actualizar datos globales
                    window.currentSubobjetivos = subobjetivosActualizados;
                    
                    // Renderizar
                    renderizarSubobjetivosFocusCompleto(subobjetivosActualizados);
                    recargaExitosa = true;
                    console.log('✅ Recarga exitosa con método 2');
                } catch (error) {
                    console.error('❌ Error en método 2:', error);
                }
            }
            
            // Método 3: Recarga manual del DOM
            if (!recargaExitosa) {
                console.log('🔄 Método 3: Recarga manual del DOM...');
                try {
                    const responseManual = await fetch(`/api/objetivos/${objetivoEnFocus.id}/subobjetivos`);
                    const subobjetivosManual = await responseManual.json();
                    
                    const container = document.getElementById('focus-subobjetivos-list');
                    if (container) {
                        // Limpiar container
                        container.innerHTML = '';
                        
                        // Recrear elementos
                        let html = '';
                        subobjetivosManual.forEach((sub) => {
                            html += `
                                <div class="focus-subobjetivo-item p-3 mb-2 bg-light rounded">
                                    <input type="checkbox" class="form-check-input focus-subobjetivo-checkbox me-3" 
                                           ${sub.completado ? "checked" : ""} 
                                           data-subobjetivo-id="${sub.id}">
                                    <span class="focus-subobjetivo-titulo ${sub.completado ? "text-decoration-line-through text-muted" : ""}" 
                                          data-subobjetivo-id="${sub.id}">${sub.titulo}</span>
                                </div>
                            `;
                        });
                        
                        container.innerHTML = html;
                        
                        // Actualizar datos globales
                        window.currentSubobjetivos = subobjetivosManual;
                        
                        // Aplicar patch para agregar selects
                        setTimeout(() => {
                            if (typeof agregarBotonesFocusSubobjetivos === 'function') {
                                agregarBotonesFocusSubobjetivos();
                            }
                        }, 100);
                        
                        // Actualizar contador
                        const completados = subobjetivosManual.filter(s => s.completado).length;
                        const progresoElement = document.getElementById('focus-progreso');
                        if (progresoElement) {
                            progresoElement.textContent = `${completados}/${subobjetivosManual.length}`;
                        }
                        
                        recargaExitosa = true;
                        console.log('✅ Recarga exitosa con método 3');
                    }
                } catch (error) {
                    console.error('❌ Error en método 3:', error);
                }
            }
            
            if (recargaExitosa) {
                // Mostrar mensaje de éxito
                const direccionTexto = direccion === 'arriba' ? 'subido' : 'bajado';
                if (typeof showSuccess === 'function') {
                    showSuccess(`Subobjetivo ${direccionTexto} correctamente`);
                } else {
                    console.log(`✅ Subobjetivo ${direccionTexto} correctamente`);
                }
            } else {
                console.error('❌ No se pudo recargar la vista, pero el cambio se guardó en el servidor');
                if (typeof showError === 'function') {
                    showError('Cambio guardado, pero necesitas recargar la página para verlo');
                }
            }
        } else {
            console.error('❌ Error al actualizar el orden en el servidor');
            if (typeof showError === 'function') {
                showError('Error al actualizar el orden del subobjetivo');
            }
        }
        
    } catch (error) {
        console.error('💥 Error al mover subobjetivo:', error);
        if (typeof showError === 'function') {
            showError('Error al mover el subobjetivo: ' + error.message);
        }
    }
}