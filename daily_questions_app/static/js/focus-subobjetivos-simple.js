// ===== VERSIÓN SIMPLIFICADA DEL MODO FOCUS PARA SUB-OBJETIVOS =====

// Variables locales (no dependen de otros archivos)
let focusSubData = {
    objetivoId: null,
    subobjetivoId: null,
    titulo: '',
    tiempoAcumulado: 0,
    timerSeconds: 0,
    timerRunning: false,
    timerInterval: null
};

// Función para inicializar el focus de un sub-objetivo
window.iniciarFocusSubobjetivo = async function(objetivoId, subobjetivoId, titulo) {
    // console.log('🎯 SIMPLE: Iniciando focus para sub-objetivo:', { objetivoId, subobjetivoId, titulo });
    
    try {
        // Obtener datos del subobjetivo
        const response = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
        const subobjetivos = await response.json();
        const subobjetivo = subobjetivos.find(s => s.id == subobjetivoId);
        
        if (!subobjetivo) {
            console.error('❌ SIMPLE: Sub-objetivo no encontrado');
            return;
        }
        
        // Configurar datos locales
        focusSubData.objetivoId = objetivoId;
        focusSubData.subobjetivoId = subobjetivoId;
        focusSubData.titulo = titulo;
        focusSubData.tiempoAcumulado = subobjetivo.tiempo_focus || 0;
        focusSubData.timerSeconds = focusSubData.tiempoAcumulado;
        
        // console.log('💾 SIMPLE: Datos configurados:', focusSubData);
        
        // Actualizar display si existe
        actualizarDisplaySimple();
        
        return focusSubData;
        
    } catch (error) {
        console.error('💥 SIMPLE: Error:', error);
    }
};

// Función para guardar tiempo
window.guardarTiempoSimple = async function() {
    if (!focusSubData.subobjetivoId) {
        console.error('❌ SIMPLE: No hay subobjetivo configurado');
        return false;
    }
    
    // console.log(`💾 SIMPLE: Guardando ${focusSubData.timerSeconds} segundos para subobjetivo ${focusSubData.subobjetivoId}`);
    
    try {
        const response = await fetch(`/api/subobjetivos/${focusSubData.subobjetivoId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tiempo_focus: focusSubData.timerSeconds })
        });

        const result = await response.json();
        // console.log('📥 SIMPLE: Response:', response.status, result);
        
        if (response.ok) {
            // console.log('✅ SIMPLE: Guardado exitoso');
            return true;
        } else {
            console.error('❌ SIMPLE: Error en guardado');
            return false;
        }
    } catch (error) {
        console.error('💥 SIMPLE: Error de red:', error);
        return false;
    }
};

// Función para iniciar timer
window.iniciarTimerSimple = function() {
    if (focusSubData.timerRunning) return;
    
    focusSubData.timerRunning = true;
    focusSubData.timerInterval = setInterval(() => {
        focusSubData.timerSeconds++;
        actualizarDisplaySimple();
        // console.log(`⏱️ SIMPLE: Timer: ${focusSubData.timerSeconds}s`);
    }, 1000);
    
    console.log('▶️ SIMPLE: Timer iniciado');
};

// Función para pausar timer
window.pausarTimerSimple = function() {
    if (!focusSubData.timerRunning) return;
    
    focusSubData.timerRunning = false;
    clearInterval(focusSubData.timerInterval);
    
    // console.log('⏸️ SIMPLE: Timer pausado');
    
    // Guardar automáticamente al pausar
    guardarTiempoSimple();
};

// Función para actualizar display
function actualizarDisplaySimple() {
    const display = document.getElementById('timer-sub-display');
    if (display) {
        const horas = Math.floor(focusSubData.timerSeconds / 3600);
        const minutos = Math.floor((focusSubData.timerSeconds % 3600) / 60);
        const segundos = focusSubData.timerSeconds % 60;
        
        display.textContent = `${horas.toString().padStart(2, '0')}:${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
    }
}

// Función para obtener estado actual
window.obtenerEstadoSimple = function() {
    return { ...focusSubData };
};

// Función de test completo
window.testCompletoSimple = async function(objetivoId, subobjetivoId, titulo) {
    console.log('🧪 SIMPLE: Iniciando test completo...');
    
    // 1. Inicializar
    await iniciarFocusSubobjetivo(objetivoId, subobjetivoId, titulo);
    
    // 2. Simular tiempo
    focusSubData.timerSeconds += 30; // Agregar 30 segundos
    console.log('🧪 SIMPLE: Tiempo simulado agregado');
    
    // 3. Guardar
    const guardado = await guardarTiempoSimple();
    
    // 4. Verificar
    if (guardado) {
        console.log('🧪 SIMPLE: Verificando guardado...');
        await iniciarFocusSubobjetivo(objetivoId, subobjetivoId, titulo);
        console.log('🧪 SIMPLE: Tiempo después de recargar:', focusSubData.tiempoAcumulado);
    }
    
    return guardado;
};

// console.log('✅ SIMPLE: Funciones de focus simplificadas cargadas');
// console.log('💡 SIMPLE: Usa testCompletoSimple(objetivoId, subobjetivoId, titulo) para probar');