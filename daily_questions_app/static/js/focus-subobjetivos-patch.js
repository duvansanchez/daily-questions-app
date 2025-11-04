// Parche para agregar botones de focus a los subobjetivos
// Este archivo se ejecuta después de cargar los subobjetivos para agregar los botones

// Variable global para almacenar datos de subobjetivos
window.currentSubobjetivos = [];
let patcheandoSubobjetivos = false;

// Función para agregar botones de focus a subobjetivos existentes
function agregarBotonesFocusSubobjetivos() {
    if (patcheandoSubobjetivos) {
        console.log('⏳ Parche ya en ejecución, omitiendo...');
        return;
    }
    
    patcheandoSubobjetivos = true;
    console.log('🔧 Aplicando parche para botones de focus en subobjetivos...');
    
    const container = document.getElementById('focus-subobjetivos-list');
    if (!container) {
        console.log('❌ Container de subobjetivos no encontrado');
        return;
    }
    
    const items = container.querySelectorAll('.focus-subobjetivo-item');
    console.log(`🔍 Encontrados ${items.length} items de subobjetivos`);
    
    items.forEach(item => {
        // Verificar si ya tiene botón de focus
        if (item.querySelector('.focus-subobjetivo-btn')) {
            return; // Ya tiene botón
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
        
        // Reestructurar el item
        const content = document.createElement('div');
        content.className = 'focus-subobjetivo-content';
        
        const actions = document.createElement('div');
        actions.className = 'focus-subobjetivo-actions';
        
        // Mover checkbox y título al content
        content.appendChild(checkbox);
        content.appendChild(titulo);
        
        // Crear botón de focus
        const focusBtn = document.createElement('button');
        focusBtn.className = 'btn btn-sm btn-outline-primary focus-subobjetivo-btn';
        focusBtn.title = 'Modo Focus para este subobjetivo';
        focusBtn.setAttribute('data-subobjetivo-id', subobjetivoId);
        focusBtn.setAttribute('data-subobjetivo-titulo', tituloTexto);
        focusBtn.innerHTML = '<i class="bi bi-bullseye"></i>';
        
        if (isCompleted) {
            focusBtn.disabled = true;
        }
        
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
        
        actions.appendChild(focusBtn);
        
        // Limpiar item y agregar nueva estructura
        item.innerHTML = '';
        item.appendChild(content);
        item.appendChild(actions);
        
        console.log(`✅ Botón de focus agregado para: ${tituloTexto}`);
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