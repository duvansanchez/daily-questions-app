// ===== MODO FOCUS PARA SUB-OBJETIVOS =====

// console.log('🔧 Cargando focus-subobjetivos.js...');

// Función auxiliar para mostrar errores de forma segura
function safeShowError(message) {
    if (typeof showError === 'function') {
        showError(message);
    } else {
        console.error(message);
        alert(message);
    }
}

// Función auxiliar para mostrar éxitos de forma segura
function safeShowSuccess(message) {
    if (typeof showSuccess === 'function') {
        showSuccess(message);
    } else {
        console.log(message);
        // No mostrar alert para éxitos, solo log
    }
}
let subobjetivoEnFocus = null;
let timerSubobjetivoInterval = null;
let timerSubobjetivoSeconds = 0;
let timerSubobjetivoRunning = false;

// Función para abrir modo focus de un sub-objetivo
async function abrirModoFocusSubobjetivo(subobjetivoId, subobjetivoTitulo) {
    // console.log('🎯 Iniciando modo focus para sub-objetivo:', subobjetivoId, subobjetivoTitulo);
    
    try {
        // Verificar que objetivoEnFocus esté definido
        if (typeof objetivoEnFocus === 'undefined' || !objetivoEnFocus) {
            console.error('❌ objetivoEnFocus no está definido');
            if (typeof showError === 'function') {
                showError('Error: No hay objetivo principal en focus');
            } else {
                alert('Error: No hay objetivo principal en focus');
            }
            return;
        }
        
        // Obtener datos del subobjetivo incluyendo tiempo acumulado
        // console.log(`📡 Obteniendo datos de subobjetivos para objetivo ${objetivoEnFocus.id}`);
        const response = await fetch(`/api/objetivos/${objetivoEnFocus.id}/subobjetivos`);
        const subobjetivos = await response.json();
        // console.log('📊 Subobjetivos recibidos:', subobjetivos);
        
        const subobjetivo = subobjetivos.find(s => s.id == subobjetivoId);
        // console.log(`🔍 Subobjetivo encontrado (ID ${subobjetivoId}):`, subobjetivo);
        
        if (!subobjetivo) {
            if (typeof showError === 'function') {
                showError('Sub-objetivo no encontrado');
            } else {
                alert('Sub-objetivo no encontrado');
            }
            return;
        }
        
        // Guardar referencia del sub-objetivo con tiempo acumulado
        subobjetivoEnFocus = {
            id: subobjetivoId,
            titulo: subobjetivoTitulo,
            tiempoAcumulado: subobjetivo.tiempo_focus || 0
        };
        
        // console.log('💾 SubobjetivoEnFocus configurado:', subobjetivoEnFocus);
        
        // Actualizar contenido del modal
        document.getElementById('focus-sub-titulo').textContent = subobjetivoTitulo;
        document.getElementById('focus-sub-objetivo-padre').textContent = objetivoEnFocus ? objetivoEnFocus.titulo : '';
        
        // Cargar tiempo acumulado
        timerSubobjetivoSeconds = subobjetivoEnFocus.tiempoAcumulado;
        // console.log(`⏱️ Timer configurado con: ${timerSubobjetivoSeconds} segundos`);
        actualizarDisplayTimerSubobjetivo();
        
        // Mostrar tiempo acumulado si existe
        if (subobjetivoEnFocus.tiempoAcumulado > 0) {
            const minutos = Math.floor(subobjetivoEnFocus.tiempoAcumulado / 60);
            const segundos = subobjetivoEnFocus.tiempoAcumulado % 60;
            const tiempoFormateado = `${minutos}:${segundos.toString().padStart(2, '0')}`;
            // console.log(`⏱️ Tiempo acumulado cargado: ${tiempoFormateado}`);
        } else {
            // console.log('⏱️ No hay tiempo acumulado previo');
        }
        
        // Cargar notas existentes
        const notasTextarea = document.getElementById('focus-sub-notas-texto');
        if (notasTextarea) {
            notasTextarea.value = subobjetivo.notas || '';
            // console.log(`📝 Notas cargadas: ${subobjetivo.notas ? subobjetivo.notas.length + ' caracteres' : 'vacías'}`);
        }
        
        // Mostrar modal del sub-objetivo
        const modalElement = document.getElementById('modalFocusSubobjetivo');
        if (!modalElement) {
            console.error('❌ Modal de focus de sub-objetivo no encontrado');
            if (typeof showError === 'function') {
                showError('Error: Modal de focus de sub-objetivo no disponible');
            } else {
                alert('Error: Modal de focus de sub-objetivo no disponible');
            }
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        
        // Inicializar editor de notas después de que el modal se muestre
        modalElement.addEventListener('shown.bs.modal', function() {
            inicializarEditorNotas();
        }, { once: true });
        
        // console.log('✅ Modal de focus de sub-objetivo abierto exitosamente');
        
    } catch (error) {
        console.error('Error al abrir modo focus de sub-objetivo:', error);
        if (typeof showError === 'function') {
            showError('Error al cargar el modo focus del sub-objetivo');
        } else {
            alert('Error al cargar el modo focus del sub-objetivo');
        }
    }
}

// Función para guardar notas del sub-objetivo
async function guardarNotasSubobjetivo() {
    if (!subobjetivoEnFocus) {
        console.log('❌ No hay sub-objetivo en focus para guardar notas');
        return false;
    }
    
    const notasTextarea = document.getElementById('focus-sub-notas-texto');
    if (!notasTextarea) {
        console.log('❌ Textarea de notas no encontrado');
        return false;
    }
    
    const notas = notasTextarea.value.trim();
    // console.log(`📝 Guardando notas del sub-objetivo: ${notas.length} caracteres`);
    
    try {
        const response = await fetch(`/api/subobjetivos/${subobjetivoEnFocus.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notas: notas })
        });

        if (response.ok) {
            // console.log('✅ Notas del sub-objetivo guardadas exitosamente');
            return true;
        } else {
            console.error('❌ Error al guardar notas del sub-objetivo');
            return false;
        }
    } catch (error) {
        console.error('💥 Error guardando notas del sub-objetivo:', error);
        return false;
    }
}

// Event listeners para botones de focus de sub-objetivos
document.addEventListener('click', function(e) {
    if (e.target.closest('.focus-subobjetivo-btn')) {
        e.preventDefault();
        const button = e.target.closest('.focus-subobjetivo-btn');
        const subobjetivoId = button.getAttribute('data-subobjetivo-id');
        const subobjetivoTitulo = button.getAttribute('data-subobjetivo-titulo');
        
        if (!subobjetivoId || !subobjetivoTitulo) {
            console.error('Botón de focus de sub-objetivo sin datos válidos');
            safeShowError('Error: Datos del sub-objetivo no válidos');
            return;
        }
        
        abrirModoFocusSubobjetivo(subobjetivoId, subobjetivoTitulo);
    }
});

// ===== TIMER PARA SUB-OBJETIVOS =====

function iniciarTimerSubobjetivo() {
    if (!timerSubobjetivoRunning) {
        timerSubobjetivoRunning = true;
        timerSubobjetivoInterval = setInterval(() => {
            timerSubobjetivoSeconds++;
            actualizarDisplayTimerSubobjetivo();
        }, 1000);

        document.getElementById('timer-sub-start').style.display = 'none';
        document.getElementById('timer-sub-pause').style.display = 'inline-block';
    }
}

function pausarTimerSubobjetivo() {
    if (timerSubobjetivoRunning) {
        timerSubobjetivoRunning = false;
        clearInterval(timerSubobjetivoInterval);

        document.getElementById('timer-sub-start').style.display = 'inline-block';
        document.getElementById('timer-sub-pause').style.display = 'none';
        
        // Guardar tiempo y notas inmediatamente al pausar
        if (subobjetivoEnFocus) {
            if (timerSubobjetivoSeconds > 0) {
                // console.log('⏸️ Timer pausado, guardando tiempo inmediatamente...');
                guardarTiempoSubobjetivo();
            }
            // console.log('⏸️ Timer pausado, guardando notas...');
            guardarNotasSubobjetivo();
        }
    }
}

async function resetearTimerSubobjetivo() {
    timerSubobjetivoRunning = false;
    timerSubobjetivoSeconds = 0;
    clearInterval(timerSubobjetivoInterval);
    actualizarDisplayTimerSubobjetivo();

    document.getElementById('timer-sub-start').style.display = 'inline-block';
    document.getElementById('timer-sub-pause').style.display = 'none';
    
    // Guardar el tiempo en 0 en la base de datos
    if (subobjetivoEnFocus) {
        // console.log('🔄 SUB: Reiniciando tiempo, guardando 0 en la base de datos...');
        const guardado = await guardarTiempoSubobjetivo(true); // forzar=true para guardar aunque sea 0
        if (guardado) {
            // console.log('✅ SUB: Tiempo reseteado y guardado exitosamente');
            safeShowSuccess('Tiempo del subobjetivo reiniciado correctamente');
        } else {
            console.error('❌ SUB: Error al guardar el tiempo reseteado');
            safeShowError('Error al reiniciar el tiempo del subobjetivo');
        }
    }
}

function actualizarDisplayTimerSubobjetivo() {
    const horas = Math.floor(timerSubobjetivoSeconds / 3600);
    const minutos = Math.floor((timerSubobjetivoSeconds % 3600) / 60);
    const segundos = timerSubobjetivoSeconds % 60;

    const display = `${horas.toString().padStart(2, '0')}:${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
    document.getElementById('timer-sub-display').textContent = display;
}

// Event listeners para controles del timer de sub-objetivos
document.addEventListener('DOMContentLoaded', function() {
    const timerSubStart = document.getElementById('timer-sub-start');
    const timerSubPause = document.getElementById('timer-sub-pause');
    const timerSubReset = document.getElementById('timer-sub-reset');
    if (timerSubStart) {
        timerSubStart.addEventListener('click', iniciarTimerSubobjetivo);
    }
    
    if (timerSubPause) {
        timerSubPause.addEventListener('click', pausarTimerSubobjetivo);
    }
    
    if (timerSubReset) {
        timerSubReset.addEventListener('click', resetearTimerSubobjetivo);
    }
});

// ===== BOTONES DE ACCIÓN PARA SUB-OBJETIVOS =====

// Completar sub-objetivo
document.addEventListener('click', async function(e) {
    if (e.target.closest('#focus-sub-completar')) {
        if (subobjetivoEnFocus) {
            try {
                // Obtener notas del textarea
                const notasTextarea = document.getElementById('focus-sub-notas-texto');
                const notas = notasTextarea ? notasTextarea.value.trim() : '';
                
                // Preparar datos para completar incluyendo tiempo final y notas
                const datosCompletar = { 
                    completado: true,
                    tiempo_focus: timerSubobjetivoSeconds,
                    notas: notas
                };

                const response = await fetch(`/api/subobjetivos/${subobjetivoEnFocus.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(datosCompletar)
                });

                if (response.ok) {
                    let mensaje = `¡Sub-objetivo "${subobjetivoEnFocus.titulo}" completado! 🎉`;
                    
                    if (timerSubobjetivoSeconds > 0) {
                        const minutos = Math.floor(timerSubobjetivoSeconds / 60);
                        const segundos = timerSubobjetivoSeconds % 60;
                        const tiempoFormateado = `${minutos}:${segundos.toString().padStart(2, '0')}`;
                        mensaje += ` Tiempo total: ${tiempoFormateado}`;
                    }

                    // Cerrar modal del sub-objetivo
                    const modal = bootstrap.Modal.getInstance(document.getElementById('modalFocusSubobjetivo'));
                    if (modal) modal.hide();

                    // Recargar sub-objetivos en el modal principal
                    if (typeof objetivoEnFocus !== 'undefined' && objetivoEnFocus) {
                        if (typeof cargarSubobjetivosFocus === 'function') {
                            await cargarSubobjetivosFocus(objetivoEnFocus.id);
                        } else {
                            console.log('⚠️ cargarSubobjetivosFocus no disponible, saltando recarga');
                        }
                    }

                    safeShowSuccess(mensaje);
                } else {
                    safeShowError('Error al completar sub-objetivo');
                }
            } catch (error) {
                console.error('Error al completar sub-objetivo:', error);
                safeShowError('Error al completar sub-objetivo');
            }
        }
    }
});

// Función para guardar tiempo acumulado del sub-objetivo
async function guardarTiempoSubobjetivo(forzar = false) {
    // console.log('🔍 Verificando condiciones para guardar tiempo...');
    console.log('- subobjetivoEnFocus:', subobjetivoEnFocus);
    console.log('- timerSubobjetivoSeconds:', timerSubobjetivoSeconds);
    console.log('- forzar:', forzar);
    
    if (!subobjetivoEnFocus) {
        console.log('❌ No hay sub-objetivo en focus');
        return false;
    }
    
    if (!forzar && timerSubobjetivoSeconds <= 0) {
        console.log('❌ Tiempo es 0 o menor, no se guarda (usar forzar=true para guardar de todos modos)');
        return false;
    }
    
    try {
        // console.log(`💾 Guardando tiempo de sub-objetivo ID ${subobjetivoEnFocus.id}: ${timerSubobjetivoSeconds} segundos`);
        
        const payload = { tiempo_focus: timerSubobjetivoSeconds };
        // console.log('📤 Payload:', JSON.stringify(payload));
        
        const response = await fetch(`/api/subobjetivos/${subobjetivoEnFocus.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        // console.log('📥 Response status:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            // console.log('✅ Tiempo de sub-objetivo guardado exitosamente:', result);
            return true;
        } else {
            const errorText = await response.text();
            console.error('❌ Error al guardar tiempo de sub-objetivo:', response.status, errorText);
            return false;
        }
    } catch (error) {
        console.error('💥 Error guardando tiempo de sub-objetivo:', error);
        return false;
    }
}

// Guardar tiempo y notas cada 30 segundos mientras el timer esté corriendo
setInterval(async () => {
    if (subobjetivoEnFocus) {
        if (timerSubobjetivoRunning) {
            await guardarTiempoSubobjetivo();
        }
        await guardarNotasSubobjetivo();
    }
}, 30000);

// ===== EDITOR DE TEXTO ENRIQUECIDO PARA NOTAS =====

// Variables para el editor
let editorMode = 'edit'; // 'edit' o 'preview'
let autoSaveTimeout = null;

// Función para inicializar el editor de notas
function inicializarEditorNotas() {
    // console.log('🔧 Inicializando editor de notas...');
    
    const textarea = document.getElementById('focus-sub-notas-texto');
    const previewDiv = document.getElementById('focus-sub-notas-preview');
    const previewContent = previewDiv?.querySelector('.preview-content');
    
    if (!textarea || !previewDiv) {
        console.error('❌ Elementos del editor no encontrados:', { textarea: !!textarea, previewDiv: !!previewDiv });
        return;
    }
    
    // console.log('✅ Elementos del editor encontrados');
    
    // Event listeners para los botones de formato
    const btnBold = document.getElementById('btn-bold');
    const btnItalic = document.getElementById('btn-italic');
    const btnPreview = document.getElementById('btn-preview');
    const btnSaveNotes = document.getElementById('btn-save-notes');
    const btnRemoveHighlight = document.getElementById('btn-remove-highlight');
    
    // console.log('🔍 Botones encontrados:', {
    //     bold: !!btnBold,
    //     italic: !!btnItalic,
    //     preview: !!btnPreview,
    //     save: !!btnSaveNotes,
    //     removeHighlight: !!btnRemoveHighlight
    // });
    
    // Remover event listeners existentes para evitar duplicados
    if (btnBold) {
        btnBold.removeEventListener('click', btnBold._formatHandler);
        btnBold._formatHandler = () => aplicarFormato('**', '**');
        btnBold.addEventListener('click', btnBold._formatHandler);
    }
    if (btnItalic) {
        btnItalic.removeEventListener('click', btnItalic._formatHandler);
        btnItalic._formatHandler = () => aplicarFormato('*', '*');
        btnItalic.addEventListener('click', btnItalic._formatHandler);
    }
    
    const btnTask = document.getElementById('btn-task');
    const btnBullet = document.getElementById('btn-bullet');
    
    if (btnTask) {
        btnTask.removeEventListener('click', btnTask._taskHandler);
        btnTask._taskHandler = () => añadirTarea();
        btnTask.addEventListener('click', btnTask._taskHandler);
    }
    if (btnBullet) {
        btnBullet.removeEventListener('click', btnBullet._bulletHandler);
        btnBullet._bulletHandler = () => añadirViñeta();
        btnBullet.addEventListener('click', btnBullet._bulletHandler);
    }
    if (btnPreview) {
        // Remover event listener existente para evitar duplicados
        btnPreview.removeEventListener('click', btnPreview._previewHandler);
        btnPreview._previewHandler = () => {
            // console.log('👁️ Alternando vista previa');
            togglePreview();
        };
        btnPreview.addEventListener('click', btnPreview._previewHandler);
    }
    if (btnSaveNotes) {
        btnSaveNotes.removeEventListener('click', btnSaveNotes._saveHandler);
        btnSaveNotes._saveHandler = () => guardarNotasManual();
        btnSaveNotes.addEventListener('click', btnSaveNotes._saveHandler);
    }
    
    // Auto-guardado mientras se escribe (remover listener existente primero)
    textarea.removeEventListener('input', textarea._inputHandler);
    textarea._inputHandler = () => {
        mostrarEstadoGuardado('saving');
        
        // Cancelar timeout anterior
        if (autoSaveTimeout) {
            clearTimeout(autoSaveTimeout);
        }
        
        // Programar guardado automático
        autoSaveTimeout = setTimeout(async () => {
            const guardado = await guardarNotasSubobjetivo();
            mostrarEstadoGuardado(guardado ? 'saved' : 'error');
        }, 2000);
    };
    textarea.addEventListener('input', textarea._inputHandler);
    
    // Atajos de teclado (remover listener existente primero)
    textarea.removeEventListener('keydown', textarea._keydownHandler);
    textarea._keydownHandler = (e) => {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key.toLowerCase()) {
                case 'b':
                    e.preventDefault();
                    aplicarFormato('**', '**');
                    break;
                case 'i':
                    e.preventDefault();
                    aplicarFormato('*', '*');
                    break;
                case 's':
                    e.preventDefault();
                    guardarNotasManual();
                    break;
                // NO interceptar otras teclas como Ctrl+Z, Ctrl+Y, Ctrl+A, etc.
                // Dejar que el navegador maneje el resto de atajos
            }
        }
    };
    textarea.addEventListener('keydown', textarea._keydownHandler);
    
    // console.log('✅ Editor de notas inicializado correctamente');
    
    // Iniciar directamente en modo preview por defecto (sin parpadeo)
    // console.log('👁️ Configurando modo preview por defecto...');
    // Reutilizar las variables ya declaradas arriba
    
    if (textarea && previewDiv && btnPreview) {
        // Configurar directamente en modo preview
        editorMode = 'preview';
        textarea.style.display = 'none';
        previewDiv.style.display = 'block';
        btnPreview.classList.add('active');
        btnPreview.innerHTML = '<i class="bi bi-pencil"></i>';
        btnPreview.title = 'Editar';
        
        // Renderizar contenido inmediatamente
        renderizarPreview();
        // console.log('✅ Modo preview configurado directamente');
    } else {
        console.error('❌ No se pudo configurar modo preview:', { 
            textarea: !!textarea, 
            previewDiv: !!previewDiv, 
            btnPreview: !!btnPreview 
        });
    }
}

// Función para aplicar formato al texto seleccionado
function aplicarFormato(inicio, fin, placeholder) {
    const textarea = document.getElementById('focus-sub-notas-texto');
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end);
    
    if (selectedText) {
        // Si hay texto seleccionado, aplicar formato
        const newText = inicio + selectedText + fin;
        textarea.value = textarea.value.substring(0, start) + newText + textarea.value.substring(end);
        textarea.setSelectionRange(start, start + newText.length);
    } else {
        // Si no hay texto seleccionado, solo insertar los marcadores
        const newText = inicio + fin;
        textarea.value = textarea.value.substring(0, start) + newText + textarea.value.substring(end);
        // Posicionar cursor entre los marcadores
        textarea.setSelectionRange(start + inicio.length, start + inicio.length);
    }
    
    textarea.focus();
    
    // Trigger input event para auto-guardado
    textarea.dispatchEvent(new Event('input'));
}

// Función para aplicar resaltado con color
function aplicarResaltado(color) {
    const textarea = document.getElementById('focus-sub-notas-texto');
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end);
    const textToInsert = selectedText || 'texto resaltado';
    
    const newText = `==${color}:${textToInsert}==`;
    
    // Reemplazar texto seleccionado
    textarea.value = textarea.value.substring(0, start) + newText + textarea.value.substring(end);
    
    // Posicionar cursor
    if (selectedText) {
        textarea.setSelectionRange(start, start + newText.length);
    } else {
        textarea.setSelectionRange(start + `==${color}:`.length, start + `==${color}:`.length + 'texto resaltado'.length);
    }
    
    textarea.focus();
    
    // Trigger input event para auto-guardado
    textarea.dispatchEvent(new Event('input'));
}

// Función para quitar resaltado del texto seleccionado
function quitarResaltado() {
    const textarea = document.getElementById('focus-sub-notas-texto');
    if (!textarea) return;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end);
    
    if (!selectedText) {
        // Si no hay texto seleccionado, buscar resaltado alrededor del cursor
        const beforeCursor = textarea.value.substring(0, start);
        const afterCursor = textarea.value.substring(end);
        
        // Buscar el inicio del resaltado más cercano hacia atrás
        const highlightStartMatch = beforeCursor.match(/==\w+:([^=]*)$/);
        if (highlightStartMatch) {
            const highlightStart = beforeCursor.lastIndexOf(highlightStartMatch[0]);
            const highlightEndMatch = afterCursor.match(/^([^=]*)==/);
            
            if (highlightEndMatch) {
                const highlightEnd = end + highlightEndMatch[0].length;
                const fullHighlight = textarea.value.substring(highlightStart, highlightEnd);
                const cleanText = fullHighlight.replace(/==\w+:([^=]*)==/, '$1');
                
                textarea.value = textarea.value.substring(0, highlightStart) + cleanText + textarea.value.substring(highlightEnd);
                textarea.setSelectionRange(highlightStart, highlightStart + cleanText.length);
            }
        }
    } else {
        // Quitar resaltado del texto seleccionado
        const cleanText = selectedText.replace(/==\w+:([^=]*)==/g, '$1');
        textarea.value = textarea.value.substring(0, start) + cleanText + textarea.value.substring(end);
        textarea.setSelectionRange(start, start + cleanText.length);
    }
    
    textarea.focus();
    
    // Trigger input event para auto-guardado
    textarea.dispatchEvent(new Event('input'));
}
function añadirTarea() {
    const textarea = document.getElementById('focus-sub-notas-texto');
    if (!textarea) return;
    
    const cursorPos = textarea.selectionStart;
    const textBefore = textarea.value.substring(0, cursorPos);
    const textAfter = textarea.value.substring(cursorPos);
    
    // Verificar si estamos al inicio de una línea
    const needsNewLine = textBefore.length > 0 && !textBefore.endsWith('\n');
    const taskText = (needsNewLine ? '\n' : '') + '- [] ';
    
    textarea.value = textBefore + taskText + textAfter;
    textarea.setSelectionRange(cursorPos + taskText.length, cursorPos + taskText.length);
    textarea.focus();
    
    // Trigger input event para auto-guardado
    textarea.dispatchEvent(new Event('input'));
}

// Función para añadir viñeta
function añadirViñeta() {
    const textarea = document.getElementById('focus-sub-notas-texto');
    if (!textarea) return;
    
    const cursorPos = textarea.selectionStart;
    const textBefore = textarea.value.substring(0, cursorPos);
    const textAfter = textarea.value.substring(cursorPos);
    
    // Verificar si estamos al inicio de una línea
    const needsNewLine = textBefore.length > 0 && !textBefore.endsWith('\n');
    const bulletText = (needsNewLine ? '\n' : '') + '- ';
    
    textarea.value = textBefore + bulletText + textAfter;
    textarea.setSelectionRange(cursorPos + bulletText.length, cursorPos + bulletText.length);
    textarea.focus();
    
    // Trigger input event para auto-guardado
    textarea.dispatchEvent(new Event('input'));
}

// Variable para prevenir múltiples toggles simultáneos
let toggleInProgress = false;

// Función para alternar vista previa
function togglePreview() {
    // Prevenir múltiples ejecuciones simultáneas
    if (toggleInProgress) {
        console.log('⚠️ Toggle ya en progreso, ignorando...');
        return;
    }
    
    toggleInProgress = true;
    
    const textarea = document.getElementById('focus-sub-notas-texto');
    const previewDiv = document.getElementById('focus-sub-notas-preview');
    const previewBtn = document.getElementById('btn-preview');
    
    // console.log('🔄 Toggle preview - elementos:', {
    //     textarea: !!textarea,
    //     previewDiv: !!previewDiv,
    //     previewBtn: !!previewBtn,
    //     currentMode: editorMode
    // });
    
    if (!textarea || !previewDiv || !previewBtn) {
        console.error('❌ Elementos necesarios para preview no encontrados');
        toggleInProgress = false;
        return;
    }
    
    try {
        if (editorMode === 'edit') {
            // Cambiar a vista previa
            // console.log('👁️ Cambiando a vista previa');
            editorMode = 'preview';
            textarea.style.display = 'none';
            previewDiv.style.display = 'block';
            previewBtn.classList.add('active');
            previewBtn.innerHTML = '<i class="bi bi-pencil"></i>';
            previewBtn.title = 'Editar';
            
            // Renderizar contenido
            renderizarPreview();
        } else {
            // Cambiar a edición
            // console.log('✏️ Cambiando a edición');
            editorMode = 'edit';
            textarea.style.display = 'block';
            previewDiv.style.display = 'none';
            previewBtn.classList.remove('active');
            previewBtn.innerHTML = '<i class="bi bi-eye"></i>';
            previewBtn.title = 'Vista previa';
            textarea.focus();
        }
    } finally {
        // Liberar el lock después de un pequeño delay
        setTimeout(() => {
            toggleInProgress = false;
        }, 100);
    }
}

// Función para renderizar la vista previa
function renderizarPreview() {
    const textarea = document.getElementById('focus-sub-notas-texto');
    const previewContent = document.querySelector('#focus-sub-notas-preview .preview-content');
    
    // console.log('🎨 Renderizando preview - elementos:', {
    //     textarea: !!textarea,
    //     previewContent: !!previewContent
    // });
    
    if (!textarea || !previewContent) {
        console.error('❌ Elementos para renderizar no encontrados');
        return;
    }
    
    let content = textarea.value;
    // console.log('📝 Contenido a renderizar:', content.substring(0, 100) + '...');
    
    // Dividir en líneas para procesamiento más preciso
    let lines = content.split('\n');
    let processedLines = [];
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        if (line === '') {
            // Línea vacía - añadir espacio solo si no estamos entre elementos de lista
            processedLines.push('<br>');
            continue;
        }
        
        // Procesar tareas completadas (ambos formatos)
        if (line.match(/^- \[x\] (.*)$/) || line.match(/^- \[X\] (.*)$/)) {
            let taskText = line.replace(/^- \[[xX]\] (.*)$/, '$1');
            // Aplicar formato de texto a las tareas
            taskText = taskText
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/==(\w+):(.*?)==/g, '<span class="highlight-$1">$2</span>')
                .replace(/==(.*?)==/g, '<span class="highlight-yellow">$1</span>');
            processedLines.push(`<div class="task-item"><input type="checkbox" class="task-checkbox" checked disabled> <span class="task-completed">${taskText}</span></div>`);
            continue;
        }
        
        // Procesar tareas pendientes (ambos formatos)
        if (line.match(/^- \[ \] (.*)$/) || line.match(/^- \[\] (.*)$/)) {
            let taskText = line.replace(/^- \[[\s]*\] (.*)$/, '$1');
            // Aplicar formato de texto a las tareas
            taskText = taskText
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/==(\w+):(.*?)==/g, '<span class="highlight-$1">$2</span>')
                .replace(/==(.*?)==/g, '<span class="highlight-yellow">$1</span>');
            processedLines.push(`<div class="task-item"><input type="checkbox" class="task-checkbox" disabled> <span>${taskText}</span></div>`);
            continue;
        }
        
        // Procesar listas con viñetas (que no sean tareas)
        if (line.match(/^- (.*)$/) && !line.match(/^- \[/)) {
            let listText = line.replace(/^- (.*)$/, '$1');
            // Aplicar formato de texto a las listas
            listText = listText
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/==(\w+):(.*?)==/g, '<span class="highlight-$1">$2</span>')
                .replace(/==(.*?)==/g, '<span class="highlight-yellow">$1</span>');
            processedLines.push(`<li>${listText}</li>`);
            continue;
        }
        
        // Procesar texto normal con formato
        line = line
            // Negritas
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Cursivas
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Resaltado con colores específicos
            .replace(/==(\w+):(.*?)==/g, '<span class="highlight-$1">$2</span>')
            // Resaltado genérico (amarillo por defecto)
            .replace(/==(.*?)==/g, '<span class="highlight-yellow">$1</span>');
        
        processedLines.push(`<p>${line}</p>`);
    }
    
    // Unir las líneas procesadas
    content = processedLines.join('');
    
    // Envolver elementos <li> consecutivos en <ul>
    content = content.replace(/(<li>.*?<\/li>)(\s*<li>.*?<\/li>)*/g, function(match) {
        return '<ul>' + match + '</ul>';
    });
    
    // Envolver elementos de tarea consecutivos en contenedor
    content = content.replace(/(<div class="task-item">.*?<\/div>)(\s*<div class="task-item">.*?<\/div>)*/g, function(match) {
        return '<div class="task-list">' + match + '</div>';
    });
    
    // Limpiar <br> innecesarios entre elementos de bloque
    content = content
        .replace(/<\/div><br><div/g, '</div><div')
        .replace(/<\/ul><br><ul/g, '</ul><ul>')
        .replace(/<\/p><br><p/g, '</p><p>')
        .replace(/<br><\/div>/g, '</div>')
        .replace(/<div[^>]*><br>/g, function(match) { return match.replace('<br>', ''); });
    
    // console.log('✅ Contenido renderizado:', content.substring(0, 200) + '...');
    previewContent.innerHTML = content || '<em class="text-muted">No hay contenido para mostrar</em>';
}

// Función para guardar notas manualmente
async function guardarNotasManual() {
    mostrarEstadoGuardado('saving');
    const guardado = await guardarNotasSubobjetivo();
    mostrarEstadoGuardado(guardado ? 'saved' : 'error');
    
    if (guardado) {
        // Mostrar feedback visual
        const btn = document.getElementById('btn-save-notes');
        if (btn) {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-check"></i>';
            btn.classList.add('btn-success');
            btn.classList.remove('btn-outline-success');
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('btn-success');
                btn.classList.add('btn-outline-success');
            }, 1500);
        }
    }
}

// Función para mostrar el estado de guardado
function mostrarEstadoGuardado(estado) {
    const statusElement = document.getElementById('notes-save-status');
    if (!statusElement) return;
    
    statusElement.className = 'text-muted ' + estado;
    
    switch (estado) {
        case 'saving':
            statusElement.innerHTML = '<i class="bi bi-cloud-arrow-up"></i> Guardando...';
            break;
        case 'saved':
            statusElement.innerHTML = '<i class="bi bi-cloud-check"></i> Guardado automáticamente';
            break;
        case 'error':
            statusElement.innerHTML = '<i class="bi bi-cloud-slash"></i> Error al guardar';
            break;
    }
}

// Limpiar timer al cerrar modal de sub-objetivo
document.addEventListener('DOMContentLoaded', function() {
    const modalSubobjetivo = document.getElementById('modalFocusSubobjetivo');
    if (modalSubobjetivo) {
        modalSubobjetivo.addEventListener('hidden.bs.modal', async function() {
            // Guardar tiempo y notas antes de cerrar
            if (subobjetivoEnFocus) {
                if (timerSubobjetivoSeconds > 0) {
                    await guardarTiempoSubobjetivo();
                }
                await guardarNotasSubobjetivo();
            }
            
            pausarTimerSubobjetivo();
            // No resetear el timer para mantener el tiempo acumulado
            subobjetivoEnFocus = null;
            
            // Resetear editor
            resetearEditor();
        });
    }
});

// Función para resetear el editor
function resetearEditor() {
    const textarea = document.getElementById('focus-sub-notas-texto');
    const previewDiv = document.getElementById('focus-sub-notas-preview');
    const previewBtn = document.getElementById('btn-preview');
    
    if (textarea && previewDiv && previewBtn) {
        // Volver al modo edición
        editorMode = 'edit';
        textarea.style.display = 'block';
        previewDiv.style.display = 'none';
        previewBtn.classList.remove('active');
        previewBtn.innerHTML = '<i class="bi bi-eye"></i>';
        previewBtn.title = 'Vista previa';
    }
    
    // Limpiar timeout de auto-guardado
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
        autoSaveTimeout = null;
    }
    
    // Resetear estado de guardado
    mostrarEstadoGuardado('saved');
    
    // Resetear variable de toggle
    toggleInProgress = false;
    
    // Limpiar event listeners para evitar acumulación
    limpiarEventListenersEditor();
}

// Función para limpiar event listeners del editor
function limpiarEventListenersEditor() {
    const textarea = document.getElementById('focus-sub-notas-texto');
    const btnBold = document.getElementById('btn-bold');
    const btnItalic = document.getElementById('btn-italic');
    const btnPreview = document.getElementById('btn-preview');
    const btnSaveNotes = document.getElementById('btn-save-notes');
    const btnTask = document.getElementById('btn-task');
    const btnBullet = document.getElementById('btn-bullet');
    
    // Remover todos los event listeners personalizados
    if (textarea && textarea._inputHandler) {
        textarea.removeEventListener('input', textarea._inputHandler);
        textarea._inputHandler = null;
    }
    if (textarea && textarea._keydownHandler) {
        textarea.removeEventListener('keydown', textarea._keydownHandler);
        textarea._keydownHandler = null;
    }
    if (btnBold && btnBold._formatHandler) {
        btnBold.removeEventListener('click', btnBold._formatHandler);
        btnBold._formatHandler = null;
    }
    if (btnItalic && btnItalic._formatHandler) {
        btnItalic.removeEventListener('click', btnItalic._formatHandler);
        btnItalic._formatHandler = null;
    }
    if (btnPreview && btnPreview._previewHandler) {
        btnPreview.removeEventListener('click', btnPreview._previewHandler);
        btnPreview._previewHandler = null;
    }
    if (btnSaveNotes && btnSaveNotes._saveHandler) {
        btnSaveNotes.removeEventListener('click', btnSaveNotes._saveHandler);
        btnSaveNotes._saveHandler = null;
    }
    if (btnTask && btnTask._taskHandler) {
        btnTask.removeEventListener('click', btnTask._taskHandler);
        btnTask._taskHandler = null;
    }
    if (btnBullet && btnBullet._bulletHandler) {
        btnBullet.removeEventListener('click', btnBullet._bulletHandler);
        btnBullet._bulletHandler = null;
    }
}

// ===== EVENT LISTENERS GLOBALES PARA RESALTADO =====
// Estos se ejecutan solo una vez para evitar duplicados

// Event listeners para colores de resaltado usando delegación
document.addEventListener('click', function(e) {
    if (e.target.closest('.highlight-color')) {
        e.preventDefault();
        const btn = e.target.closest('.highlight-color');
        const color = btn.getAttribute('data-color');
        // console.log('🎨 Aplicando color:', color);
        aplicarResaltado(color);
    }
});

// Event listener para quitar resaltado usando delegación
document.addEventListener('click', function(e) {
    if (e.target.closest('#btn-remove-highlight')) {
        e.preventDefault();
        // console.log('🧹 Quitando resaltado');
        quitarResaltado();
    }
});

// Exponer funciones globalmente para compatibilidad
window.abrirModoFocusSubobjetivo = abrirModoFocusSubobjetivo;

// console.log('✅ focus-subobjetivos.js cargado completamente');
// console.log('🔍 Función abrirModoFocusSubobjetivo disponible:', typeof abrirModoFocusSubobjetivo);
// console.log('🔍 Función en window:', typeof window.abrirModoFocusSubobjetivo);
// ===== PROCESAMIENTO DE PREFIJOS DE SUB-OBJETIVOS =====

// Función para procesar títulos con prefijos de colores
function procesarTituloConPrefijos(titulo) {
    if (!titulo) return titulo;
    
    // Definir prefijos y sus clases CSS
    const prefijos = {
        'feat:': 'prefix-feat',
        'fix:': 'prefix-fix', 
        'refactor:': 'prefix-refactor',
        'docs:': 'prefix-docs',
        'style:': 'prefix-style',
        'investigate:': 'prefix-investigate',
        'config:': 'prefix-config'
    };
    
    // Buscar si el título comienza con algún prefijo
    for (const [prefijo, clase] of Object.entries(prefijos)) {
        if (titulo.toLowerCase().startsWith(prefijo.toLowerCase())) {
            // Extraer el prefijo y el resto del título
            const prefijoTexto = titulo.substring(0, prefijo.length);
            const restoTitulo = titulo.substring(prefijo.length).trim();
            
            // Retornar HTML con el prefijo coloreado
            return `<span class="subobjetivo-prefix ${clase}">${prefijoTexto}</span>${restoTitulo}`;
        }
    }
    
    // Si no hay prefijo, retornar el título original
    return titulo;
}

// Función para aplicar prefijos a todos los sub-objetivos visibles
function aplicarPrefijosSubobjetivos() {
    const items = document.querySelectorAll('.focus-subobjetivo-titulo');
    
    items.forEach(item => {
        // Solo procesar si no ha sido procesado antes
        if (!item.hasAttribute('data-prefijo-procesado')) {
            const tituloOriginal = item.textContent;
            const tituloConPrefijo = procesarTituloConPrefijos(tituloOriginal);
            
            if (tituloConPrefijo !== tituloOriginal) {
                item.innerHTML = tituloConPrefijo;
                item.setAttribute('data-prefijo-procesado', 'true');
            }
        }
    });
}

// Exponer función globalmente
window.procesarTituloConPrefijos = procesarTituloConPrefijos;
window.aplicarPrefijosSubobjetivos = aplicarPrefijosSubobjetivos;