// ===== PERSISTENCIA DE TIEMPO PARA OBJETIVOS =====

// Variables globales del timer (si no existen)
if (typeof timerSeconds === 'undefined') {
    window.timerSeconds = 0;
}
if (typeof timerRunning === 'undefined') {
    window.timerRunning = false;
}
if (typeof timerInterval === 'undefined') {
    window.timerInterval = null;
}

// Función para resetear el timer
async function resetearTimer() {
    console.log('🔄 OBJ: Reseteando timer...');
    timerRunning = false;
    timerSeconds = 0;
    clearInterval(timerInterval);
    
    // Actualizar display
    if (typeof actualizarDisplayTimer === 'function') {
        actualizarDisplayTimer();
    } else {
        const display = document.getElementById('timer-display');
        if (display) {
            display.textContent = '00:00:00';
        }
    }
    
    // Actualizar botones
    const startBtn = document.getElementById('timer-start');
    const pauseBtn = document.getElementById('timer-pause');
    if (startBtn) startBtn.style.display = 'inline-block';
    if (pauseBtn) pauseBtn.style.display = 'none';
    
    // Guardar el tiempo en 0 en la base de datos
    if (objetivoEnFocus) {
        console.log('🔄 OBJ: Guardando tiempo en 0 en la base de datos...');
        const guardado = await guardarTiempoObjetivo(true); // forzar=true para guardar aunque sea 0
        if (guardado) {
            console.log('✅ OBJ: Tiempo reseteado y guardado exitosamente');
            showSuccess('Tiempo reiniciado correctamente');
        } else {
            console.error('❌ OBJ: Error al guardar el tiempo reseteado');
            showError('Error al reiniciar el tiempo');
        }
    }
}

// Hacer la función global
window.resetearTimer = resetearTimer;

// Función para cargar tiempo acumulado cuando se abre el modal
async function cargarTiempoAcumuladoObjetivo() {
    if (!objetivoEnFocus) return;
    
    try {
        console.log('🔄 OBJ: Cargando tiempo acumulado del objetivo...');
        const response = await fetch(`/api/objetivos/${objetivoEnFocus.id}`);
        const objetivo = await response.json();
        
        if (objetivo && objetivo.tiempo_focus) {
            timerSeconds = objetivo.tiempo_focus;
            actualizarDisplayTimer();
            
            const minutos = Math.floor(objetivo.tiempo_focus / 60);
            const segundos = objetivo.tiempo_focus % 60;
            const tiempoFormateado = `${minutos}:${segundos.toString().padStart(2, '0')}`;
            console.log(`⏱️ OBJ: Tiempo acumulado cargado: ${tiempoFormateado}`);
        } else {
            console.log('⏱️ OBJ: No hay tiempo acumulado previo');
        }
        
        // Cargar notas existentes
        const notasTextarea = document.getElementById('focus-notas-texto');
        if (notasTextarea && objetivo) {
            notasTextarea.value = objetivo.notas_adicionales || '';
            console.log(`📝 OBJ: Notas cargadas: ${objetivo.notas_adicionales ? objetivo.notas_adicionales.length + ' caracteres' : 'vacías'}`);
        }
    } catch (error) {
        console.error('💥 OBJ: Error cargando tiempo acumulado:', error);
    }
}

// Función para guardar tiempo acumulado del objetivo principal
async function guardarTiempoObjetivo(forzar = false) {
    console.log('🔍 OBJ: Verificando condiciones para guardar tiempo...');
    console.log('- objetivoEnFocus:', objetivoEnFocus);
    console.log('- timerSeconds:', timerSeconds);
    console.log('- forzar:', forzar);
    
    if (!objetivoEnFocus) {
        console.log('❌ OBJ: No hay objetivo en focus');
        return false;
    }
    
    if (!forzar && timerSeconds === 0) {
        console.log('❌ OBJ: Tiempo es 0, no se guarda (usar forzar=true para guardar de todos modos)');
        return false;
    }
    
    try {
        console.log(`💾 OBJ: Guardando tiempo de objetivo ID ${objetivoEnFocus.id}: ${timerSeconds} segundos`);
        
        const payload = { tiempo_focus: timerSeconds };
        console.log('📤 OBJ: Payload:', JSON.stringify(payload));
        
        const response = await fetch(`/api/objetivos/${objetivoEnFocus.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        console.log('📥 OBJ: Response status:', response.status);
        
        if (response.ok) {
            const result = await response.json();
            console.log('✅ OBJ: Tiempo de objetivo guardado exitosamente:', result);
            return true;
        } else {
            const errorText = await response.text();
            console.error('❌ OBJ: Error al guardar tiempo de objetivo:', response.status, errorText);
            return false;
        }
    } catch (error) {
        console.error('💥 OBJ: Error guardando tiempo de objetivo:', error);
        return false;
    }
}

// Función para guardar notas del objetivo principal
async function guardarNotasObjetivo() {
    if (!objetivoEnFocus) {
        console.log('❌ OBJ: No hay objetivo en focus para guardar notas');
        return false;
    }
    
    const notasTextarea = document.getElementById('focus-notas-texto');
    if (!notasTextarea) {
        console.log('❌ OBJ: Textarea de notas no encontrado');
        return false;
    }
    
    const notas = notasTextarea.value.trim();
    console.log(`📝 OBJ: Guardando notas del objetivo: ${notas.length} caracteres`);
    
    try {
        const response = await fetch(`/api/objetivos/${objetivoEnFocus.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notas_adicionales: notas })
        });

        if (response.ok) {
            console.log('✅ OBJ: Notas del objetivo guardadas exitosamente');
            return true;
        } else {
            console.error('❌ OBJ: Error al guardar notas del objetivo');
            return false;
        }
    } catch (error) {
        console.error('💥 OBJ: Error guardando notas del objetivo:', error);
        return false;
    }
}

// Guardar tiempo y notas cada 30 segundos mientras el timer esté corriendo
setInterval(async () => {
    if (objetivoEnFocus) {
        if (timerRunning) {
            await guardarTiempoObjetivo();
        }
        await guardarNotasObjetivo();
    }
}, 30000);

// Sobrescribir la función pausarTimer para agregar guardado automático
document.addEventListener('DOMContentLoaded', function() {
    // Esperar a que se carguen las funciones originales
    setTimeout(() => {
        if (typeof window.pausarTimer === 'function') {
            const pausarTimerOriginal = window.pausarTimer;
            
            window.pausarTimer = function() {
                console.log('⏸️ OBJ: Timer pausado, guardando tiempo y notas...');
                
                // Ejecutar función original
                pausarTimerOriginal();
                
                // Guardar tiempo y notas inmediatamente al pausar
                if (objetivoEnFocus) {
                    if (timerSeconds > 0) {
                        guardarTiempoObjetivo();
                    }
                    guardarNotasObjetivo();
                }
            };
            
            console.log('✅ OBJ: Función pausarTimer sobrescrita para guardar automáticamente');
        } else {
            console.log('⚠️ OBJ: Función pausarTimer no encontrada, creando nueva...');
            
            // Crear función pausarTimer si no existe
            window.pausarTimer = function() {
                if (timerRunning) {
                    timerRunning = false;
                    clearInterval(timerInterval);

                    const startBtn = document.getElementById('timer-start');
                    const pauseBtn = document.getElementById('timer-pause');
                    
                    if (startBtn) startBtn.style.display = 'inline-block';
                    if (pauseBtn) pauseBtn.style.display = 'none';
                    
                    // Guardar tiempo y notas inmediatamente al pausar
                    if (objetivoEnFocus) {
                        if (timerSeconds > 0) {
                            console.log('⏸️ OBJ: Timer pausado, guardando tiempo...');
                            guardarTiempoObjetivo();
                        }
                        console.log('⏸️ OBJ: Timer pausado, guardando notas...');
                        guardarNotasObjetivo();
                    }
                }
            };
        }
    }, 1000);
});

// Esta función se ejecutará cuando se abra el modal

// Configuración de botones de debug removida

// Event listener para el botón de reset
document.addEventListener('DOMContentLoaded', function() {
    const btnReset = document.getElementById('timer-reset');
    if (btnReset) {
        btnReset.addEventListener('click', resetearTimer);
        console.log('✅ OBJ: Event listener para botón reset configurado');
    }
});

// Event listeners para el modal de objetivos
document.addEventListener('DOMContentLoaded', function() {
    const modalFocus = document.getElementById('modalFocusObjetivo');
    if (modalFocus) {
        // Cuando se abre el modal, cargar tiempo acumulado
        modalFocus.addEventListener('shown.bs.modal', async function() {
            console.log('🎯 OBJ: Modal abierto, cargando tiempo acumulado...');
            setTimeout(async () => {
                await cargarTiempoAcumuladoObjetivo();
            }, 500);
        });
        
        // Cuando se cierra el modal, guardar tiempo y notas
        modalFocus.addEventListener('hidden.bs.modal', async function() {
            // Guardar tiempo y notas antes de cerrar
            if (objetivoEnFocus) {
                if (timerSeconds > 0) {
                    console.log('🚪 OBJ: Cerrando modal, guardando tiempo...');
                    await guardarTiempoObjetivo();
                }
                console.log('🚪 OBJ: Cerrando modal, guardando notas...');
                await guardarNotasObjetivo();
            }
            
            if (typeof pausarTimer === 'function') {
                pausarTimer();
            }
            // No resetear el timer para mantener el tiempo acumulado
            objetivoEnFocus = null;
        });
    }
});

// Modificar la función de completar objetivo para incluir tiempo final
document.addEventListener('DOMContentLoaded', function() {
    const btnCompletar = document.getElementById('focus-completar');
    if (btnCompletar) {
        // Remover event listeners existentes
        const newBtn = btnCompletar.cloneNode(true);
        btnCompletar.parentNode.replaceChild(newBtn, btnCompletar);
        
        // Agregar nuevo event listener
        newBtn.addEventListener('click', async function() {
            if (objetivoEnFocus) {
                try {
                    // Obtener notas del textarea
                    const notasTextarea = document.getElementById('focus-notas-texto');
                    const notas = notasTextarea ? notasTextarea.value.trim() : '';
                    
                    // Preparar datos para enviar incluyendo tiempo final y notas
                    const datosActualizacion = {
                        completado: true,
                        tiempo_focus: timerSeconds,
                        notas_adicionales: notas
                    };

                    const response = await fetch(`/api/objetivos/${objetivoEnFocus.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(datosActualizacion)
                    });

                    if (response.ok) {
                        // Mostrar mensaje con tiempo si se registró
                        let mensaje = '¡Objetivo completado! 🎉';
                        if (timerSeconds > 0) {
                            const minutos = Math.floor(timerSeconds / 60);
                            const segundos = timerSeconds % 60;
                            const tiempoFormateado = `${minutos}:${segundos.toString().padStart(2, '0')}`;
                            mensaje += ` Tiempo total registrado: ${tiempoFormateado}`;
                        }

                        // Cerrar modal
                        const modal = bootstrap.Modal.getInstance(document.getElementById('modalFocusObjetivo'));
                        if (modal) modal.hide();

                        // Recargar objetivos
                        if (typeof cargarObjetivos === 'function') {
                            await cargarObjetivos();
                        }

                        showSuccess(mensaje);
                    } else {
                        showError('Error al completar objetivo');
                    }
                } catch (error) {
                    console.error('Error al completar objetivo:', error);
                    showError('Error al completar objetivo');
                }
            }
        });
    }
});