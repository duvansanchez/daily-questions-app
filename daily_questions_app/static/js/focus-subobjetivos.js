// ===== MODO FOCUS PARA SUB-OBJETIVOS =====

// Variables globales para el modo focus de sub-objetivos
let subobjetivoEnFocus = null;
let timerSubobjetivoInterval = null;
let timerSubobjetivoSeconds = 0;
let timerSubobjetivoRunning = false;

// Función para abrir modo focus de un sub-objetivo
async function abrirModoFocusSubobjetivo(subobjetivoId, subobjetivoTitulo) {
    console.log('🎯 Iniciando modo focus para sub-objetivo:', subobjetivoId, subobjetivoTitulo);
    
    try {
        // Verificar que objetivoEnFocus esté definido
        if (!objetivoEnFocus) {
            console.error('❌ objetivoEnFocus no está definido');
            showError('Error: No hay objetivo principal en focus');
            return;
        }
        
        // Obtener datos del subobjetivo incluyendo tiempo acumulado
        console.log(`📡 Obteniendo datos de subobjetivos para objetivo ${objetivoEnFocus.id}`);
        const response = await fetch(`/api/objetivos/${objetivoEnFocus.id}/subobjetivos`);
        const subobjetivos = await response.json();
        console.log('📊 Subobjetivos recibidos:', subobjetivos);
        
        const subobjetivo = subobjetivos.find(s => s.id == subobjetivoId);
        console.log(`🔍 Subobjetivo encontrado (ID ${subobjetivoId}):`, subobjetivo);
        
        if (!subobjetivo) {
            showError('Sub-objetivo no encontrado');
            return;
        }
        
        // Guardar referencia del sub-objetivo con tiempo acumulado
        subobjetivoEnFocus = {
            id: subobjetivoId,
            titulo: subobjetivoTitulo,
            tiempoAcumulado: subobjetivo.tiempo_focus || 0
        };
        
        console.log('💾 SubobjetivoEnFocus configurado:', subobjetivoEnFocus);
        
        // Actualizar contenido del modal
        document.getElementById('focus-sub-titulo').textContent = subobjetivoTitulo;
        document.getElementById('focus-sub-objetivo-padre').textContent = objetivoEnFocus ? objetivoEnFocus.titulo : '';
        
        // Cargar tiempo acumulado
        timerSubobjetivoSeconds = subobjetivoEnFocus.tiempoAcumulado;
        console.log(`⏱️ Timer configurado con: ${timerSubobjetivoSeconds} segundos`);
        actualizarDisplayTimerSubobjetivo();
        
        // Mostrar tiempo acumulado si existe
        if (subobjetivoEnFocus.tiempoAcumulado > 0) {
            const minutos = Math.floor(subobjetivoEnFocus.tiempoAcumulado / 60);
            const segundos = subobjetivoEnFocus.tiempoAcumulado % 60;
            const tiempoFormateado = `${minutos}:${segundos.toString().padStart(2, '0')}`;
            console.log(`⏱️ Tiempo acumulado cargado: ${tiempoFormateado}`);
        } else {
            console.log('⏱️ No hay tiempo acumulado previo');
        }
        
        // Cargar notas existentes
        const notasTextarea = document.getElementById('focus-sub-notas-texto');
        if (notasTextarea) {
            notasTextarea.value = subobjetivo.notas || '';
            console.log(`📝 Notas cargadas: ${subobjetivo.notas ? subobjetivo.notas.length + ' caracteres' : 'vacías'}`);
        }
        
        // Mostrar modal del sub-objetivo
        const modalElement = document.getElementById('modalFocusSubobjetivo');
        if (!modalElement) {
            console.error('❌ Modal de focus de sub-objetivo no encontrado');
            showError('Error: Modal de focus de sub-objetivo no disponible');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        
        console.log('✅ Modal de focus de sub-objetivo abierto exitosamente');
        
    } catch (error) {
        console.error('Error al abrir modo focus de sub-objetivo:', error);
        showError('Error al cargar el modo focus del sub-objetivo');
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
    console.log(`📝 Guardando notas del sub-objetivo: ${notas.length} caracteres`);
    
    try {
        const response = await fetch(`/api/subobjetivos/${subobjetivoEnFocus.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notas: notas })
        });

        if (response.ok) {
            console.log('✅ Notas del sub-objetivo guardadas exitosamente');
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
            showError('Error: Datos del sub-objetivo no válidos');
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
                console.log('⏸️ Timer pausado, guardando tiempo inmediatamente...');
                guardarTiempoSubobjetivo();
            }
            console.log('⏸️ Timer pausado, guardando notas...');
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
        console.log('🔄 SUB: Reiniciando tiempo, guardando 0 en la base de datos...');
        const guardado = await guardarTiempoSubobjetivo(true); // forzar=true para guardar aunque sea 0
        if (guardado) {
            console.log('✅ SUB: Tiempo reseteado y guardado exitosamente');
            showSuccess('Tiempo del subobjetivo reiniciado correctamente');
        } else {
            console.error('❌ SUB: Error al guardar el tiempo reseteado');
            showError('Error al reiniciar el tiempo del subobjetivo');
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
                    if (objetivoEnFocus) {
                        await cargarSubobjetivosFocus(objetivoEnFocus.id);
                    }

                    showSuccess(mensaje);
                } else {
                    showError('Error al completar sub-objetivo');
                }
            } catch (error) {
                console.error('Error al completar sub-objetivo:', error);
                showError('Error al completar sub-objetivo');
            }
        }
    }
});

// Función para guardar tiempo acumulado del sub-objetivo
async function guardarTiempoSubobjetivo(forzar = false) {
    console.log('🔍 Verificando condiciones para guardar tiempo...');
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
        console.log(`💾 Guardando tiempo de sub-objetivo ID ${subobjetivoEnFocus.id}: ${timerSubobjetivoSeconds} segundos`);
        
        const payload = { tiempo_focus: timerSubobjetivoSeconds };
        console.log('📤 Payload:', JSON.stringify(payload));
        
        const response = await fetch(`/api/subobjetivos/${subobjetivoEnFocus.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        console.log('📥 Response status:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            console.log('✅ Tiempo de sub-objetivo guardado exitosamente:', result);
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
        });
    }
});