console.log('JS CARGADO');

// Variables globales
let currentQuestionIndex = 0;
let questions = [];
let responses = {};
let questionTimers = {}; // Para almacenar los timers de cada pregunta
let questionStartTimes = {}; // Para almacenar los tiempos de inicio
let mapaObjetivosPadre = {};
let categoriaActual = 'diario';
let frases = []; // Variable global para frases inspiracionales

// Variables para la sesión de repaso
let sesionRepaso = {
    frases: [],
    indiceActual: 0,
    frasesRepasadas: 0,
    activa: false
};

// Cronómetro de sesión
let cronometroSesion = {
    inicio: null,
    intervalo: null
};

// === HISTÓRICO DE OBJETIVOS ===
let historico = [];
let historicoOffset = 0;
let historicoLimit = 20;
let historicoFin = false;

// Variables globales para bloques de categoría (asegura que estén disponibles en todos los handlers)
const bloqueCatExistenteNueva = document.getElementById('bloque-categoria-existente-nueva');
const bloqueNuevaCatNueva = document.getElementById('bloque-nueva-categoria-nueva');

// Integración de SweetAlert2 para alertas globales
// Asegúrate de incluir el script de SweetAlert2 en tu HTML

// Alerta de éxito
function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: 'Éxito',
        text: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 2500,
        timerProgressBar: true
    });
}

// Alerta de error
function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'Error',
        text: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 4000,
        timerProgressBar: true
    });
}

// Alerta de información
function showInfo(message) {
    Swal.fire({
        icon: 'info',
        title: 'Información',
        text: message,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 2500,
        timerProgressBar: true
    });
}

// Confirmación (retorna una promesa)
function showConfirm(message) {
    return Swal.fire({
        title: '¿Estás seguro?',
        text: message,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sí, continuar',
        cancelButtonText: 'Cancelar',
        width: '23rem',
        customClass: {
            title: 'swal2-custom-title',
            htmlContainer: 'swal2-custom-text'
        }
    });
}

// Exportar funciones globalmente
window.showSuccess = showSuccess;
window.showError = showError;
window.showInfo = showInfo;
window.showConfirm = showConfirm;

// Función para cargar subobjetivos en vista de lista
async function cargarSubobjetivosLista(objetivoId) {
    try {
        console.log('Cargando subobjetivos para objetivo:', objetivoId);
        const response = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
        console.log('Response status:', response.status);
        const subobjetivos = await response.json();
        console.log('Subobjetivos recibidos:', subobjetivos);
        
        const container = document.getElementById(`subobjetivos-lista-${objetivoId}`);
        if (!container) return;
        
        container.innerHTML = '';
        
        if (subobjetivos.length === 0) {
            container.innerHTML = `
                <div class="subobjetivo-lista-item">
                    <span class="subobjetivo-lista-titulo" style="color: #9ca3af; font-style: italic;">
                        No hay subobjetivos
                    </span>
                </div>
            `;
            return;
        }
        
        subobjetivos.forEach(sub => {
            const subItem = document.createElement('div');
            subItem.className = 'subobjetivo-lista-item';
            subItem.innerHTML = `
                <input type="checkbox" class="subobjetivo-lista-checkbox" ${sub.completado ? 'checked' : ''} 
                       data-subobjetivo-id="${sub.id}" data-objetivo-id="${objetivoId}">
                <span class="subobjetivo-lista-titulo ${sub.completado ? 'completado' : ''}">${sub.titulo}</span>
                <div class="subobjetivo-lista-acciones">
                    <button class="subobjetivo-lista-btn" title="Eliminar" data-subobjetivo-id="${sub.id}">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            container.appendChild(subItem);
        });
        
        // Agregar event listeners para los checkboxes de subobjetivos
        container.querySelectorAll('.subobjetivo-lista-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', async function() {
                const subobjetivoId = this.getAttribute('data-subobjetivo-id');
                const objetivoId = this.getAttribute('data-objetivo-id');
                const completado = this.checked;
                
                try {
                    const response = await fetch(`/api/subobjetivos/${subobjetivoId}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ completado })
                    });
                    
                    if (response.ok) {
                        const titulo = this.nextElementSibling;
                        if (completado) {
                            titulo.classList.add('completado');
                        } else {
                            titulo.classList.remove('completado');
                        }
                    }
                } catch (error) {
                    console.error('Error actualizando subobjetivo:', error);
                    this.checked = !completado; // Revertir el cambio
                }
            });
        });
        
        // Agregar event listeners para eliminar subobjetivos
        container.querySelectorAll('.subobjetivo-lista-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                const subobjetivoId = this.getAttribute('data-subobjetivo-id');
                
                if (confirm('¿Estás seguro de que quieres eliminar este subobjetivo?')) {
                    try {
                        const response = await fetch(`/api/subobjetivos/${subobjetivoId}`, {
                            method: 'DELETE'
                        });
                        
                        if (response.ok) {
                            this.closest('.subobjetivo-lista-item').remove();
                        }
                    } catch (error) {
                        console.error('Error eliminando subobjetivo:', error);
                    }
                }
            });
        });
        
    } catch (error) {
        console.error('Error cargando subobjetivos:', error);
    }
}

// Funciones para manejar el contador de tiempo
function startQuestionTimer(questionId) {
    // Detener timer anterior si existe
    if (questionTimers[questionId]) {
        clearInterval(questionTimers[questionId]);
    }
    
    // Registrar tiempo de inicio
    questionStartTimes[questionId] = Date.now();
    
    // Crear elemento de timer si no existe
    let timerElement = document.getElementById(`timer-${questionId}`);
    if (!timerElement) {
        const questionCard = document.querySelector(`[data-question-id="${questionId}"]`);
        if (questionCard) {
            // Crear el elemento del timer
            const timerContainer = document.createElement('div');
            timerContainer.className = 'timer-container';
            timerContainer.innerHTML = `
                <div class="timer-display">
                    <i class="fas fa-clock"></i>
                    <span id="timer-${questionId}">0:00</span>
                </div>
            `;
            
            // Insertar el timer en la pregunta
            const questionHeader = questionCard.querySelector('.question-header');
            if (questionHeader) {
                questionHeader.appendChild(timerContainer);
            }
        }
        timerElement = document.getElementById(`timer-${questionId}`);
    }
    
    // Iniciar el contador
    questionTimers[questionId] = setInterval(() => {
        const elapsed = Math.floor((Date.now() - questionStartTimes[questionId]) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        if (timerElement) {
            timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

function stopQuestionTimer(questionId) {
    if (questionTimers[questionId]) {
        clearInterval(questionTimers[questionId]);
        delete questionTimers[questionId];
    }
}

function getQuestionResponseTime(questionId) {
    if (questionStartTimes[questionId]) {
        return Math.floor((Date.now() - questionStartTimes[questionId]) / 1000);
    }
    return null;
}

// Función para mostrar notificaciones
function showNotification(message, type = 'info', timeout = 3000) {
    let container = document.getElementById('notification-container');
    if (!container) {
        // Crear contenedor si no existe
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    try {
        const notif = document.createElement('div');
        notif.className = `alert alert-${type}`;
        notif.textContent = message;
        notif.style.marginBottom = '8px';
        if (container) {
            container.insertBefore(notif, container.firstChild);
            setTimeout(() => {
                notif.remove();
            }, timeout);
        } else {
            // Fallback si por alguna razón no existe el contenedor
            alert(message);
        }
    } catch (err) {
        // Fallback si algo falla
        alert(message);
    }
}

// Función para manejar errores de fetch
function handleFetchError(error) {
    console.error('Error:', error);
    showNotification('Ha ocurrido un error. Por favor, intenta nuevamente.', 'danger');
}

// Función para mostrar la pregunta actual
function showQuestion(index) {
    // Ocultar todas las preguntas
    document.querySelectorAll('.question-card').forEach((card, i) => {
        if (i === index) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
    
    // Actualizar la barra de progreso
    const progress = ((index + 1) / questions.length) * 100;
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text span:last-child');
    
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', index + 1);
    progressText.textContent = `${index + 1} de ${questions.length}`;
    
    // Actualizar botones de navegación
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const submitBtn = document.getElementById('submit-btn');
    
    prevBtn.disabled = index === 0;
    
    if (index === questions.length - 1) {
        nextBtn.style.display = 'none';
        submitBtn.style.display = 'inline-block';
    } else {
        nextBtn.style.display = 'inline-block';
        submitBtn.style.display = 'none';
    }
    
    // Iniciar timer para la pregunta actual
    const questionId = questions[index].id;
    startQuestionTimer(questionId);
    
    // Restaurar respuesta guardada si existe
    if (responses[questionId]) {
        const optionBtns = document.querySelectorAll(`.question-card[style*='display: block'] .option-btn`);
        optionBtns.forEach(btn => {
            if (btn.dataset.option === responses[questionId]) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });
    }
}

// Función para guardar la respuesta actual
function saveCurrentResponse() {
    const currentQuestion = questions[currentQuestionIndex];
    if (!currentQuestion) return;
    const card = currentQuestion.element;
    let value = null;

    // 1. Botones personalizados (option-btn)
    const selectedBtn = card.querySelector('.option-btn.selected');
    if (selectedBtn) {
        value = selectedBtn.dataset.option;
    }

    // 2. Checkbox (varias opciones)
    const checkboxes = card.querySelectorAll('input[type="checkbox"]');
    if (checkboxes.length > 0) {
        const checked = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value);
        if (checked.length > 0) {
            value = checked.join(',');
        }
    }

    // 3. Radio (una opción)
    const radios = card.querySelectorAll('input[type="radio"]');
    if (radios.length > 0) {
        const checkedRadio = Array.from(radios).find(r => r.checked);
        if (checkedRadio) {
            value = checkedRadio.value;
        }
    }

    // 4. Textarea (texto libre)
    const textarea = card.querySelector('textarea');
    if (textarea) {
        if (textarea.value.trim() !== '') {
            value = textarea.value.trim();
        }
    }

    // Guardar siempre la respuesta (vacía o no) para preguntas no obligatorias
    const isRequired = card.getAttribute('data-is-required') == '1' || card.getAttribute('data-is-required') == 'true';
    if (isRequired) {
    if (value !== null && value !== undefined && value !== '') {
        responses[currentQuestion.id] = value;
    } else {
        delete responses[currentQuestion.id];
        }
    } else {
        // No obligatoria: guardar aunque esté vacía
        responses[currentQuestion.id] = value !== null && value !== undefined ? value : '';
    }
}

// Utilidad para obtener fecha local en formato YYYY-MM-DD
function getFechaLocalYMD(date) {
    return date.getFullYear() + '-' +
        String(date.getMonth() + 1).padStart(2, '0') + '-' +
        String(date.getDate()).padStart(2, '0');
}

// Función para enviar las respuestas al servidor
async function submitResponses() {
    try {
        console.log('Respuestas que se enviarán:', responses);
        // Obtener la fecha seleccionada del dropdown
        const fechaSelect = document.getElementById('fecha-respuesta-select');
        let fechaParaEnviar;
        if (fechaSelect && fechaSelect.value === 'ayer') {
            const ayer = new Date();
            ayer.setDate(ayer.getDate() - 1);
            fechaParaEnviar = getFechaLocalYMD(ayer);
        } else {
            const hoy = new Date();
            fechaParaEnviar = getFechaLocalYMD(hoy);
        }
        console.log('Fecha que se enviará:', fechaParaEnviar);
        
        // Preparar respuestas con tiempo
        const responsesWithTime = {};
        for (const [questionId, answer] of Object.entries(responses)) {
            const responseTime = getQuestionResponseTime(questionId);
            const startTime = questionStartTimes[questionId] ? new Date(questionStartTimes[questionId]).toISOString() : null;
            
            responsesWithTime[questionId] = {
                answer: answer,
                start_time: startTime,
                response_time: responseTime
            };
            
            // Detener el timer de esta pregunta
            stopQuestionTimer(questionId);
        }
        
        const response = await fetch('/submit_responses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date: fechaParaEnviar,
                responses: responsesWithTime
            })
        });
        
        const result = await response.json();
        if (result.status === 'success') {
            showNotification('¡Tus respuestas han sido guardadas exitosamente!', 'success');
            // Redirigir a la página de estadísticas o dashboard
            setTimeout(() => {
                window.location.href = '/stats';
            }, 1500);
        } else {
            throw new Error(result.message || 'Error al guardar las respuestas');
        }
    } catch (error) {
        console.error('Error al enviar respuestas:', error);
        showNotification('Error al enviar las respuestas. Por favor, inténtalo de nuevo.', 'danger');
    }
}

// Event listeners globales
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar variables
    questions = Array.from(document.querySelectorAll('.question-card')).map((card) => ({
        id: card.getAttribute('data-question-id'),
        element: card
    }));
    
    // Mostrar la primera pregunta
    if (questions.length > 0) {
        showQuestion(0);
    }
    
    // Manejar clic en opciones de respuesta
    document.addEventListener('click', function(e) {
        if (e.target.closest('.option-btn')) {
            const optionBtn = e.target.closest('.option-btn');
            const questionCard = optionBtn.closest('.question-card');
            
            // Deseleccionar otras opciones
            questionCard.querySelectorAll('.option-btn').forEach(btn => {
                btn.classList.remove('selected');
            });
            
            // Seleccionar la opción actual
            optionBtn.classList.add('selected');
        }
    });
    
    // Manejar botón Anterior
    const prevBtn = document.getElementById('prev-btn');
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            if (currentQuestionIndex > 0) {
                saveCurrentResponse();
                currentQuestionIndex--;
                showQuestion(currentQuestionIndex);
            }
        });
    }
    
    // Manejar botón Siguiente
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            saveCurrentResponse();
            currentQuestionIndex++;
            showQuestion(currentQuestionIndex);
        });
    }
    
    // Manejar botón Enviar
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function() {
            saveCurrentResponse();
            // Validar preguntas obligatorias antes de enviar
            const obligatoriasSinResponder = questions.filter(q => {
                const card = q.element;
                const isRequired = card.getAttribute('data-is-required') == '1' || card.getAttribute('data-is-required') == 'true';
                return isRequired && !(q.id in responses) && !card.querySelector('.option-btn.selected') && !card.querySelector('input[type="checkbox"]:checked') && !card.querySelector('input[type="radio"]:checked') && (!card.querySelector('textarea') || card.querySelector('textarea').value.trim() === '');
            });
            if (obligatoriasSinResponder.length > 0) {
                showError('Debes responder todas las preguntas obligatorias antes de enviar.');
                return;
            }
            showConfirm('¿Estás seguro de que deseas enviar tus respuestas?').then((result) => {
                if (result.isConfirmed) {
                    submitResponses();
                }
            });
        });
    }

    // Validación del submit solo del campo visible
    const form = document.getElementById('add-question-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Submit capturado'); // Para depuración
            // Solo valida los bloques de categoría si es el formulario de preguntas
            if (form.id === 'add-question-form') {
                const bloqueCatExistenteNueva = document.getElementById('bloque-categoria-existente-nueva');
                const bloqueNuevaCatNueva = document.getElementById('bloque-nueva-categoria-nueva');
            if (!bloqueCatExistenteNueva || !bloqueNuevaCatNueva) {
                console.error('No se encontraron los bloques de categoría.');
                return;
                }
            }
            const submitBtn = document.getElementById('submit-question');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Guardando...';
            const formData = new FormData(form);
            let categoriaExistente = '';
            let nuevaCategoria = '';
            if (bloqueCatExistenteNueva && bloqueCatExistenteNueva.style.display !== 'none') {
                categoriaExistente = formData.get('categoria_existente') || '';
            }
            if (bloqueNuevaCatNueva && bloqueNuevaCatNueva.style.display !== 'none') {
                nuevaCategoria = formData.get('nueva_categoria') || '';
            }
            if (categoriaExistente && nuevaCategoria) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Crear Pregunta';
                showError('No puedes seleccionar una categoría existente y escribir una nueva al mismo tiempo.');
                return false;
            }
            // Construir el objeto de datos para enviar
            const data = {
                text: formData.get('text') || '',
                type: formData.get('type') || 'text',
                options: formData.get('options') || '',
                descripcion: formData.get('descripcion') || '',
                is_required: document.getElementById('is_required').checked ? 1 : 0,
                categoria_existente: categoriaExistente,
                nueva_categoria: nuevaCategoria
            };
            try {
                const response = await fetch('/add_question', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                if (result.status === 'success') {
                    showSuccess('Pregunta creada exitosamente');
                    setTimeout(() => {
                        window.location.href = window.location.href.split('?')[0];
                    }, 1200);
                } else {
                    showError(result.message || 'Error al crear la pregunta');
                }
            } catch (err) {
                showError('Error al crear la pregunta: ' + (err.message || err));
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Crear Pregunta';
            }
        });
    }

    // ================= FRECUENCIA DE RESPUESTA (Intermedias) =================

    // Solo inicializar si existe el tab de frecuencia
    const frecuenciaTab = document.getElementById('frecuencia');
    if (frecuenciaTab) {
    // Elementos
    const preguntaSelector = document.getElementById('preguntaSelector');
    const periodoBtns = document.querySelectorAll('.periodo-btn');
    const tipoGraficoBtns = document.querySelectorAll('.tipo-grafico-btn');
    const graficoFrecuencia = document.getElementById('graficoFrecuencia');
    const mensajeExclusion = document.getElementById('mensajeExclusion');
    const periodoTitulo = document.getElementById('periodoTitulo');

    let chartInstance = null;
    let preguntasData = window.preguntasData || [];

    // Helper para saber si es texto abierto
    function esTextoAbierto(tipo) {
        return tipo === 'texto' || tipo === 'text' || tipo === 'open';
    }

    // Fetch real de datos desde el backend
    async function fetchFrecuenciaDatos(preguntaId, parametrosPeriodo) {
        try {
            let url = `/api/stats/frequency/${preguntaId}?periodo=${parametrosPeriodo.tipo}`;
            
            // Agregar parámetros adicionales si es un mes específico
            if (parametrosPeriodo.tipo === 'mes') {
                url += `&mes=${parametrosPeriodo.mes}&anio=${parametrosPeriodo.anio}`;
            }
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                if (errorData.excluded) {
                    throw new Error('excluded');
                }
                throw new Error(errorData.error || 'Error al obtener datos');
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            if (error.message === 'excluded') {
                throw error;
            }
            console.error('Error fetching frequency data:', error);
            throw new Error('Error al obtener datos de frecuencia');
        }
    }

    // Renderizar gráfico
    function renderGrafico(datos, tipoGrafico) {
        if (chartInstance) {
            chartInstance.destroy();
        }
        const ctx = document.createElement('canvas');
        ctx.height = 350;
        graficoFrecuencia.innerHTML = '';
        graficoFrecuencia.appendChild(ctx);

        const chartType = datos.tipo === 'barras' ? 'bar' : (tipoGrafico === 'lineas' ? 'line' : 'bar');

        const options = {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: { display: true, position: 'top' },
                title: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            return `${label}: ${value}`;
                        }
                    }
                },
                datalabels: {
                    display: true,
                    color: function(context) {
                        const bg = context.dataset.backgroundColor;
                        if (Array.isArray(bg)) {
                            return bg[context.dataIndex] === '#ef4444' ? '#fff' : '#fff';
                        }
                        return '#fff';
                    },
                    anchor: 'end',
                    align: 'start',
                    font: {
                        weight: 'bold',
                        size: 16
                    },
                    formatter: function(value) {
                        return value;
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } },
                x: { ticks: { maxRotation: 45, minRotation: 0 } }
            }
        };

        chartInstance = new Chart(ctx, {
            type: chartType,
            data: {
                labels: datos.labels,
                datasets: datos.datasets
            },
            options: options,
            plugins: [ChartDataLabels]
        });
    }

    // Actualizar todo según selección
    async function actualizarFrecuencia() {
        const preguntaSelector = document.getElementById('preguntaSelector');
        if (!preguntaSelector || !preguntaSelector.value) {
            // Mostrar estado inicial
            const graficoFrecuencia = document.getElementById('graficoFrecuencia');
            if (graficoFrecuencia) {
                graficoFrecuencia.innerHTML = `
                    <div class="d-flex align-items-center justify-content-center h-100 text-muted" style="min-height: 400px;">
                        <div class="text-center">
                            <i class="bi bi-bar-chart" style="font-size: 4rem; opacity: 0.3;"></i>
                            <div class="mt-3">
                                <h6>¡Comienza tu análisis!</h6>
                                <p class="mb-0">Selecciona una pregunta arriba para ver el gráfico de frecuencia de respuestas</p>
                            </div>
                        </div>
                    </div>
                `;
            }
            return;
        }

        const selectedOption = preguntaSelector.options[preguntaSelector.selectedIndex];
        const tipo = selectedOption.getAttribute('data-tipo');
        const periodoRadio = document.querySelector('.periodo-radio:checked');
        const graficoRadio = document.querySelector('.grafico-radio:checked');
        const periodo = periodoRadio ? periodoRadio.value : '7dias';
        const tipoGrafico = graficoRadio ? graficoRadio.value : 'barras';

        // Obtener parámetros específicos según el período
        let parametrosPeriodo = { tipo: periodo };
        if (periodo === 'mes') {
            const selectorMes = document.getElementById('selector-mes');
            const selectorAnio = document.getElementById('selector-anio');
            parametrosPeriodo.mes = selectorMes ? parseInt(selectorMes.value) : new Date().getMonth();
            parametrosPeriodo.anio = selectorAnio ? parseInt(selectorAnio.value) : new Date().getFullYear();
        }

        // Actualizar títulos
        const tituloGrafico = document.getElementById('tituloGrafico');
        const subtituloGrafico = document.getElementById('subtituloGrafico');
        if (tituloGrafico) {
            tituloGrafico.textContent = `Análisis: ${selectedOption.text}`;
        }
        if (subtituloGrafico) {
            let periodoTexto = '';
            switch(periodo) {
                case '7dias': 
                    periodoTexto = 'Últimos 7 días'; 
                    break;
                case 'mes': 
                    const meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
                    const mesNombre = meses[parametrosPeriodo.mes] || 'Mes';
                    periodoTexto = `${mesNombre} ${parametrosPeriodo.anio}`;
                    break;
            }
            subtituloGrafico.textContent = `${periodoTexto} • Visualización: ${tipoGrafico}`;
        }

        // Limpiar estado anterior
        const graficoFrecuencia = document.getElementById('graficoFrecuencia');
        const mensajeExclusion = document.getElementById('mensajeExclusion');
        const mensajeSinDatos = document.getElementById('mensajeSinDatos');
        
        if (graficoFrecuencia) graficoFrecuencia.innerHTML = '';
        if (mensajeExclusion) mensajeExclusion.classList.add('d-none');
        if (mensajeSinDatos) mensajeSinDatos.classList.add('d-none');

        if (esTextoAbierto(tipo)) {
            if (mensajeExclusion) mensajeExclusion.classList.remove('d-none');
            return;
        }

        try {
            // Mostrar indicador de carga
            if (graficoFrecuencia) {
                graficoFrecuencia.innerHTML = `
                    <div class="d-flex align-items-center justify-content-center h-100" style="min-height: 400px;">
                        <div class="text-center">
                            <div class="spinner-border text-primary mb-3" role="status"></div>
                            <div class="text-muted">Analizando respuestas...</div>
                        </div>
                    </div>
                `;
            }
            
            // Obtener datos reales
            const datos = await fetchFrecuenciaDatos(selectedOption.value, parametrosPeriodo);
            
            // Verificar si hay datos
            if (!datos.labels || datos.labels.length === 0) {
                if (mensajeSinDatos) mensajeSinDatos.classList.remove('d-none');
                if (graficoFrecuencia) {
                    graficoFrecuencia.innerHTML = `
                        <div class="d-flex align-items-center justify-content-center h-100 text-muted" style="min-height: 400px;">
                            <div class="text-center">
                                <i class="bi bi-inbox" style="font-size: 4rem; opacity: 0.3;"></i>
                                <div class="mt-3">
                                    <h6>Sin datos suficientes</h6>
                                    <p class="mb-0">No hay respuestas para esta pregunta en el período seleccionado</p>
                                </div>
                            </div>
                        </div>
                    `;
                }
                return;
            }
            
            // Renderizar gráfico
            renderGrafico(datos, tipoGrafico);
            
        } catch (error) {
            console.error('Error en actualizarFrecuencia:', error);
            
            if (error.message === 'excluded') {
                if (mensajeExclusion) mensajeExclusion.classList.remove('d-none');
            } else {
                if (graficoFrecuencia) {
                    graficoFrecuencia.innerHTML = `
                        <div class="d-flex align-items-center justify-content-center h-100" style="min-height: 400px;">
                            <div class="text-center text-danger">
                                <i class="bi bi-exclamation-triangle" style="font-size: 4rem; opacity: 0.5;"></i>
                                <div class="mt-3">
                                    <h6>Error al cargar datos</h6>
                                    <p class="mb-0 text-muted">${error.message}</p>
                                </div>
                            </div>
                        </div>
                    `;
                }
            }
        }
    }

    // Eventos para la nueva interfaz
    if (preguntaSelector) {
        preguntaSelector.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const tipo = selectedOption.getAttribute('data-tipo');
            
            // Actualizar información del tipo de pregunta
            const tipoInfo = document.getElementById('tipoPreguntaInfo');
            if (tipoInfo) {
                if (this.value) {
                    let tipoTexto = '';
                    let icono = '';
                    switch(tipo) {
                        case 'yes_no':
                        case 'boolean':
                            tipoTexto = 'Pregunta de Sí/No - Ideal para análisis de frecuencia';
                            icono = 'bi-check-circle text-success';
                            break;
                        case 'radio':
                        case 'select':
                            tipoTexto = 'Pregunta de opción múltiple - Perfecta para análisis';
                            icono = 'bi-list-ul text-primary';
                            break;
                        case 'checkbox':
                            tipoTexto = 'Pregunta de selección múltiple - Análisis disponible';
                            icono = 'bi-check2-square text-info';
                            break;
                        case 'texto':
                        case 'text':
                        case 'open':
                            tipoTexto = 'Pregunta de texto abierto - No disponible para análisis cuantitativo';
                            icono = 'bi-pencil text-warning';
                            break;
                        default:
                            tipoTexto = 'Tipo de pregunta: ' + tipo;
                            icono = 'bi-question-circle text-muted';
                    }
                    tipoInfo.innerHTML = `<i class="${icono} me-1"></i>${tipoTexto}`;
                } else {
                    tipoInfo.innerHTML = '<i class="bi bi-info-circle me-1"></i>Selecciona una pregunta para ver su tipo';
                }
            }
            
            // Habilitar/deshabilitar botones
            const btnActualizar = document.getElementById('btnActualizarGrafico');
            const btnExportar = document.getElementById('btnExportarGrafico');
            if (btnActualizar) btnActualizar.disabled = !this.value;
            if (btnExportar) btnExportar.disabled = !this.value;
            
            actualizarFrecuencia();
        });
    }

    // Inicializar selector de años
    function inicializarSelectorAnios() {
        const selectorAnio = document.getElementById('selector-anio');
        if (selectorAnio) {
            const anioActual = new Date().getFullYear();
            selectorAnio.innerHTML = '';
            
            // Agregar años desde el actual hacia atrás (últimos 5 años)
            for (let i = 0; i < 5; i++) {
                const anio = anioActual - i;
                const option = document.createElement('option');
                option.value = anio;
                option.textContent = anio;
                if (i === 0) option.selected = true; // Seleccionar año actual por defecto
                selectorAnio.appendChild(option);
            }
        }
    }

    // Inicializar selector de mes actual
    function inicializarSelectorMes() {
        const selectorMes = document.getElementById('selector-mes');
        if (selectorMes) {
            const mesActual = new Date().getMonth();
            selectorMes.value = mesActual;
        }
    }

    // Eventos para radio buttons de período
    const periodoRadios = document.querySelectorAll('.periodo-radio');
    periodoRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const selectorMesContainer = document.getElementById('selector-mes-container');
            
            if (this.value === 'mes') {
                // Mostrar selector de mes
                if (selectorMesContainer) {
                    selectorMesContainer.style.display = 'block';
                }
            } else {
                // Ocultar selector de mes
                if (selectorMesContainer) {
                    selectorMesContainer.style.display = 'none';
                }
            }
            
            if (this.checked) {
                actualizarFrecuencia();
            }
        });
    });

    // Eventos para selectores de mes y año
    const selectorMes = document.getElementById('selector-mes');
    const selectorAnio = document.getElementById('selector-anio');
    
    if (selectorMes) {
        selectorMes.addEventListener('change', function() {
            const periodoMes = document.getElementById('periodo-mes');
            if (periodoMes && periodoMes.checked) {
                actualizarFrecuencia();
            }
        });
    }
    
    if (selectorAnio) {
        selectorAnio.addEventListener('change', function() {
            const periodoMes = document.getElementById('periodo-mes');
            if (periodoMes && periodoMes.checked) {
                actualizarFrecuencia();
            }
        });
    }

    // Inicializar selectores
    inicializarSelectorAnios();
    inicializarSelectorMes();

    // Eventos para radio buttons de tipo de gráfico
    const graficoRadios = document.querySelectorAll('.grafico-radio');
    graficoRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                actualizarFrecuencia();
            }
        });
    });

    // Botón actualizar
    const btnActualizar = document.getElementById('btnActualizarGrafico');
    if (btnActualizar) {
        btnActualizar.addEventListener('click', actualizarFrecuencia);
    }

    // Botón exportar
    const btnExportar = document.getElementById('btnExportarGrafico');
    if (btnExportar) {
        btnExportar.addEventListener('click', function() {
            if (window.chartInstance) {
                const preguntaSelector = document.getElementById('preguntaSelector');
                const selectedOption = preguntaSelector.options[preguntaSelector.selectedIndex];
                const filename = `frecuencia_${selectedOption.text.replace(/[^a-zA-Z0-9]/g, '_')}.png`;
                
                const link = document.createElement('a');
                link.download = filename;
                link.href = window.chartInstance.toBase64Image();
                link.click();
            }
        });
    }
    }

    // === Objetivos Desarrollo Personal ===
    console.log('Buscando botón de modal...');
    const btnAbrirModalObjetivo = document.getElementById('btn-abrir-modal-objetivo');
    if (btnAbrirModalObjetivo) {
        console.log('Botón de modal encontrado');
        btnAbrirModalObjetivo.addEventListener('click', function(e) {
            e.preventDefault();
            limpiarCamposNuevoObjetivo();
            const modalNuevoObjetivo = document.getElementById('modalNuevoObjetivo');
            if (modalNuevoObjetivo) {
                const modal = new bootstrap.Modal(modalNuevoObjetivo);
                modal.show();
            }
        });
    } else {
        console.log('Botón de modal NO encontrado');
    }

    // === Objetivos Generales ===
    async function actualizarResumenObjetivos() {
        // Filtrar por categoría
        const diarios = objetivos.filter(obj => ((obj.categoria || 'diario').toLowerCase()) === 'diario' && !(obj.recurrente && obj.saltado_hoy));
        const diariosCompletados = diarios.filter(obj => obj.completado).length;
        const elDiarios = document.getElementById('objetivos-diarios');
        if (elDiarios) {
            elDiarios.textContent = `${diariosCompletados}/${diarios.length}`;
        }
        // Progreso semanal
        const semanales = objetivos.filter(obj => ((obj.categoria || 'diario').toLowerCase()) === 'semanal' && !(obj.recurrente && obj.saltado_hoy));
        const semanalesCompletados = semanales.filter(obj => obj.completado).length;
        const elSemanal = document.getElementById('objetivos-semanales');
        if (elSemanal) {
            elSemanal.textContent = `${semanalesCompletados}/${semanales.length}`;
        }
        // Progreso mensual
        const mensuales = objetivos.filter(obj => ((obj.categoria || 'diario').toLowerCase()) === 'mensual' && !(obj.recurrente && obj.saltado_hoy));
        const mensualesCompletados = mensuales.filter(obj => obj.completado).length;
        const elMensual = document.getElementById('objetivos-mensuales');
        if (elMensual) {
            elMensual.textContent = `${mensualesCompletados}/${mensuales.length}`;
        }
        // Progreso anual
        const anuales = objetivos.filter(obj => ((obj.categoria || 'diario').toLowerCase()) === 'anual' && !(obj.recurrente && obj.saltado_hoy));
        const anualesCompletados = anuales.filter(obj => obj.completado).length;
        const elAnual = document.getElementById('objetivos-anuales');
        if (elAnual) {
            elAnual.textContent = `${anualesCompletados}/${anuales.length}`;
        }
        // Objetivos generales
        const generales = objetivos.filter(obj => ((obj.categoria || '').toLowerCase()) === 'general');
        const generalesCompletados = generales.filter(obj => obj.completado).length;
        const elGenerales = document.getElementById('objetivos-generales');
        if (elGenerales) {
            elGenerales.textContent = `${generalesCompletados}/${generales.length}`;
        }
}

// === Objetivos Desarrollo Personal (Integración API) ===
let objetivos = [];
let ordenActual = 'completado'; // Variable global para el ordenamiento
let vistaActual = 'lista'; // Variable global para el tipo de vista

async function cargarObjetivos() {
    try {
        const res = await fetch('/api/objetivos');
        objetivos = await res.json();
        // Obtener mapa de objetivos padre
        try {
            const resPadre = await fetch('/api/objetivos_padre');
            const padres = await resPadre.json();
            mapaObjetivosPadre = {};
            padres.forEach(p => { mapaObjetivosPadre[p.id] = p.titulo; });
        } catch {}
        renderObjetivos();
    } catch (err) {
        objetivos = [];
        renderObjetivos();
        showError('Error al cargar objetivos');
    }
}
window.cargarObjetivos = cargarObjetivos;
window.cargarYRenderizarSubobjetivos = cargarYRenderizarSubobjetivos;

// Función para ordenar objetivos
function ordenarObjetivos(objetivos, criterio) {
    const objetivosOrdenados = [...objetivos];
    
    switch (criterio) {
        case 'orden':
            return objetivosOrdenados.sort((a, b) => (a.orden || 0) - (b.orden || 0));
        case 'fecha_creacion':
            return objetivosOrdenados.sort((a, b) => {
                const fechaA = a.fecha_creacion ? new Date(a.fecha_creacion) : new Date(0);
                const fechaB = b.fecha_creacion ? new Date(b.fecha_creacion) : new Date(0);
                return fechaB - fechaA; // Más recientes primero
            });
        case 'completado':
            return objetivosOrdenados.sort((a, b) => {
                // Pendientes primero, luego completados
                if (a.completado !== b.completado) {
                    return a.completado ? 1 : -1;
                }
                // Si ambos tienen el mismo estado, ordenar por fecha de creación descendente
                const fechaA = a.fecha_creacion ? new Date(a.fecha_creacion) : new Date(0);
                const fechaB = b.fecha_creacion ? new Date(b.fecha_creacion) : new Date(0);
                return fechaB - fechaA;
            });
        case 'prioridad':
            const prioridadOrden = { 'alta': 3, 'media': 2, 'baja': 1 };
            return objetivosOrdenados.sort((a, b) => {
                const prioridadA = prioridadOrden[a.prioridad] || 0;
                const prioridadB = prioridadOrden[b.prioridad] || 0;
                if (prioridadA === prioridadB) {
                    // Si tienen la misma prioridad, ordenar por fecha de creación
                    const fechaA = a.fecha_creacion ? new Date(a.fecha_creacion) : new Date(0);
                    const fechaB = b.fecha_creacion ? new Date(b.fecha_creacion) : new Date(0);
                    return fechaB - fechaA;
                }
                return prioridadB - prioridadA; // Alta prioridad primero
            });
        case 'titulo':
            return objetivosOrdenados.sort((a, b) => {
                const tituloA = (a.titulo || '').toLowerCase();
                const tituloB = (b.titulo || '').toLowerCase();
                return tituloA.localeCompare(tituloB);
            });
        default:
            return objetivosOrdenados;
    }
}

function renderObjetivos() {
    const lista = document.getElementById('lista-objetivos');
    lista.innerHTML = '';
    
    // Cambiar clase del contenedor según la vista
    if (vistaActual === 'lista') {
        lista.className = 'objetivos-lista';
    } else {
        lista.className = 'objetivos-grid';
    }
    let filtrados;
    if (categoriaActual === 'todos') {
        filtrados = objetivos;
    } else {
        filtrados = objetivos.filter(obj => ((obj.categoria || 'diario').toLowerCase()) === categoriaActual.toLowerCase());
    }

    // Forzar booleano robusto
    filtrados = filtrados.map(obj => ({
        ...obj,
        completado: obj.completado === true || obj.completado === 1 || obj.completado === "true" || obj.completado === "1" || obj.completado === 'True'
    }));

    // Aplicar ordenamiento
    filtrados = ordenarObjetivos(filtrados, ordenActual);

    if (filtrados.length === 0) {
        lista.innerHTML = '<li class="list-group-item text-center text-muted">No hay objetivos para esta categoría.</li>';
        actualizarResumenObjetivos();
        return;
    }

    let primerCompletadoEncontrado = false;
    let prioridadActual = null;
    filtrados.forEach((obj, idx) => {
        // Separador visual para completados
        if (ordenActual === 'completado' && obj.completado && !primerCompletadoEncontrado) {
            const separador = document.createElement('div');
            if (vistaActual === 'lista') {
                separador.className = 'objetivo-lista-separador';
                separador.innerHTML = '<div class="objetivo-lista-separador-texto">Objetivos Completados</div>';
            } else {
                separador.className = 'separador-objetivos';
                separador.innerHTML = '<hr class="my-3"><div class="text-center text-muted fw-semibold mb-2">Objetivos Completados</div>';
            }
            lista.appendChild(separador);
            primerCompletadoEncontrado = true;
        }
        // Separador visual para prioridad
        if (ordenActual === 'prioridad' && obj.prioridad !== prioridadActual) {
            if (prioridadActual !== null) {
                const separador = document.createElement('div');
                separador.className = 'separador-objetivos';
                separador.innerHTML = '<hr class="my-2">';
                lista.appendChild(separador);
            }
            prioridadActual = obj.prioridad;
        }
        // Mostrar número de orden arriba derecha y flechas abajo derecha solo en orden personalizado
        let ordenNumHtml = '';
        let ordenFlechasHtml = '';
        if (ordenActual === 'orden') {
            ordenNumHtml = `<span class=\"orden-objetivo-num\">${obj.orden}</span>`;
            ordenFlechasHtml = `<div class=\"orden-objetivo-container orden-objetivo-inline\">
                <button class=\"objetivo-main-up-btn\" title=\"Subir\" data-id=\"${obj.id}\" ${idx === 0 ? 'disabled' : ''}>&#9650;</button>
                <button class=\"objetivo-main-down-btn\" title=\"Bajar\" data-id=\"${obj.id}\" ${idx === filtrados.length - 1 ? 'disabled' : ''}>&#9660;</button>
            </div>`;
        }
        // Formateo de fechas en español
        const fechaCreacion = obj.fecha_creacion ? new Date(obj.fecha_creacion + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
        const fechaInicio = obj.fecha_inicio ? new Date(obj.fecha_inicio + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
        const fechaFin = obj.fecha_fin ? new Date(obj.fecha_fin + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
        // Crear elemento según la vista
        const elemento = document.createElement('div');
        
        if (vistaActual === 'lista') {
            // Vista de lista
            elemento.className = 'objetivo-lista-item';
            if (obj.completado) elemento.classList.add('objetivo-completado');
            if (obj.saltado_hoy) elemento.classList.add('objetivo-inactivo-hoy');
            if (!obj.completado && !obj.saltado_hoy && obj.estado !== 'histórico') elemento.classList.add('resaltado-activo');
            
            // Crear etiquetas para la vista de lista
            let etiquetas = [];
            if (obj.prioridad) {
                etiquetas.push(`<span class="objetivo-lista-etiqueta prioridad-${obj.prioridad}">${obj.prioridad.charAt(0).toUpperCase() + obj.prioridad.slice(1)}</span>`);
            }
            if (obj.categoria) {
                etiquetas.push(`<span class="objetivo-lista-etiqueta categoria">${obj.categoria.charAt(0).toUpperCase() + obj.categoria.slice(1)}</span>`);
            }
            if (fechaFin) {
                etiquetas.push(`<span class="objetivo-lista-etiqueta fecha"><i class='bi bi-calendar-check me-1'></i>${new Date(obj.fecha_fin + 'T12:00:00').toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}</span>`);
            }
            if (obj.horas_estimadas) {
                etiquetas.push(`<span class="objetivo-lista-etiqueta horas"><i class='bi bi-clock me-1'></i>${formatearHorasMinutos(obj.horas_estimadas)}</span>`);
            }
            if (obj.recompensa) {
                etiquetas.push(`<span class="objetivo-lista-etiqueta recompensa"><i class='bi bi-gift me-1'></i>${obj.recompensa}</span>`);
            }
            
            elemento.innerHTML = `
                <div class="objetivo-lista-principal">
                    <input type="checkbox" class="objetivo-lista-checkbox check-objetivo" ${obj.completado ? 'checked' : ''} data-id="${obj.id}">
                    <div class="objetivo-lista-contenido">
                        <h6 class="objetivo-lista-titulo ${obj.completado ? 'completado' : ''}">${obj.titulo}</h6>
                        ${obj.descripcion ? `<p class="objetivo-lista-descripcion">${obj.descripcion}</p>` : ''}
                        ${etiquetas.length > 0 ? `<div class="objetivo-lista-meta">${etiquetas.join('')}</div>` : ''}
                    </div>
                    <div class="objetivo-lista-acciones">
                        <button class="objetivo-lista-btn toggle-subobjetivos" title="Mostrar/ocultar subobjetivos" data-objetivo-id="${obj.id}">
                            <i class="bi bi-chevron-down"></i>
                        </button>
                        <button class="objetivo-lista-btn editar" title="Editar" data-id="${obj.id}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="objetivo-lista-btn eliminar" title="Eliminar" data-id="${obj.id}">
                            <i class="bi bi-trash"></i>
                        </button>
                        ${obj.recurrente && !obj.saltado_hoy && !obj.completado ? `<button class="objetivo-lista-btn saltar" title="Saltar hoy" data-id="${obj.id}">Saltar hoy</button>` : ''}
                        ${obj.recurrente && obj.saltado_hoy && !obj.completado ? `<button class="objetivo-lista-btn reactivar" title="Reactivar hoy" data-id="${obj.id}">Reactivar hoy</button>` : ''}
                    </div>
                </div>
                <div class="objetivo-lista-subobjetivos" id="subobjetivos-lista-${obj.id}" style="display: none;">
                    <!-- Los subobjetivos se cargarán aquí -->
                </div>
            `;
        } else {
            // Vista de tarjetas (código existente)
            elemento.className = 'objetivo-card mb-3';
            if (obj.completado) elemento.classList.add('objetivo-completado');
            if (obj.saltado_hoy) elemento.classList.add('objetivo-inactivo-hoy');
            if (!obj.completado && !obj.saltado_hoy && obj.estado !== 'histórico') elemento.classList.add('resaltado-activo');
            elemento.innerHTML = `
            <div style=\"flex:1;min-width:0;position:relative;\">
                <input type=\"checkbox\" class=\"form-check-input me-2 check-objetivo\" ${obj.completado ? 'checked' : ''} data-id=\"${obj.id}\">
                <span class=\"objetivo-titulo\">${obj.titulo}</span>
                <span class=\"etiqueta-prioridad ${obj.prioridad}\">${obj.prioridad.charAt(0).toUpperCase() + obj.prioridad.slice(1)}</span>
                ${obj.categoria ? `<span class=\"etiqueta-categoria\">${obj.categoria.charAt(0).toUpperCase() + obj.categoria.slice(1)}</span>` : ''}
                ${obj.estado ? `<span class=\"badge bg-secondary ms-1\">${obj.estado.replace('_', ' ').toUpperCase()}</span>` : ''}
                ${obj.saltado_hoy ? `<span class='badge bg-secondary ms-1'>No activo hoy</span>` : ''}
                ${obj.objetivo_padre_id && mapaObjetivosPadre[obj.objetivo_padre_id] ? `<div class='objetivo-padre small text-primary'><i class='bi bi-diagram-3'></i> Padre: ${mapaObjetivosPadre[obj.objetivo_padre_id]}</div>` : ''}
                ${obj.descripcion ? `<div class=\"objetivo-desc\">${obj.descripcion}</div>` : ''}
                <div class=\"objetivo-extra mt-1 small text-muted\">
                    ${fechaCreacion ? `<span class=\"objetivo-fecha\"><i class='bi bi-calendar-plus'></i> Creado: ${fechaCreacion}</span>` : ''}
                    ${obj.recompensa ? `<span class=\"objetivo-recompensa\"><i class='bi bi-gift'></i> ${obj.recompensa}</span>` : ''}
                    ${fechaInicio ? `<span class=\"objetivo-fecha\"><i class='bi bi-calendar-event'></i> Inicio: ${fechaInicio}</span>` : ''}
                    ${fechaFin ? `<span class=\"objetivo-fecha\"><i class='bi bi-calendar-check'></i> Fin: ${fechaFin}</span>` : ''}
                    ${obj.horas_estimadas ? `<span class=\"objetivo-horas\"><i class='bi bi-clock'></i> ${formatearHorasMinutos(obj.horas_estimadas)}</span>` : ''}
                    ${obj.dificultad ? `<span class=\"objetivo-dificultad\"><i class='bi bi-bar-chart'></i> Dificultad: ${obj.dificultad}</span>` : ''}
                    ${obj.etiquetas ? `<span class=\"objetivo-etiquetas\"><i class='bi bi-tags'></i> ${obj.etiquetas}</span>` : ''}
                </div>
                ${obj.notas_adicionales ? `<div class=\"objetivo-notas small text-info mt-1\"><i class='bi bi-info-circle'></i> ${obj.notas_adicionales}</div>` : ''}
                <div class=\"subobjetivos-container\" id=\"subobjetivos-container-${obj.id}\">
                    <div class=\"subobjetivos-list\" id=\"subobjetivos-list-${obj.id}\"></div>
                    <div class=\"subobjetivos-add\" style=\"display:none;\" id=\"subobjetivos-add-${obj.id}\">
                        <div class=\"d-flex gap-2 mt-2\">
                            <input type=\"text\" class=\"form-control form-control-sm subobjetivo-input\" placeholder=\"Nuevo subobjetivo...\">
                            <button class=\"btn btn-sm btn-primary subobjetivo-add-btn\">Agregar</button>
                        </div>
                    </div>
                    <button class=\"btn btn-outline-secondary btn-sm rounded-circle subobjetivo-toggle-btn\" data-objetivo-id=\"${obj.id}\" title=\"Mostrar checklist\" style=\"padding:0.3rem 0.5rem; font-size:1.1rem;\">
                        <i class=\"bi bi-list-check\"></i>
                    </button>
                </div>
            </div>
            <div class=\"acciones-objetivo\">
                <button class=\"btn-editar\" title=\"Editar\" data-id=\"${obj.id}\"><i class=\"bi bi-pencil\"></i></button>
                <button class=\"btn-eliminar\" title=\"Eliminar\" data-id=\"${obj.id}\"><i class=\"bi bi-trash\"></i></button>
                ${obj.recurrente && !obj.saltado_hoy && !obj.completado ? `<button class=\"btn-saltar-hoy\" title=\"Saltar hoy\" data-id=\"${obj.id}\"><i class=\"bi bi-arrow-bar-right\"></i> Saltar hoy</button>` : ''}
                ${obj.recurrente && obj.saltado_hoy && !obj.completado ? `<button class=\"btn-reactivar-hoy\" title=\"Reactivar hoy\" data-id=\"${obj.id}\"><i class=\"bi bi-arrow-repeat\"></i> Reactivar hoy</button>` : ''}
                ${(ordenActual === 'orden') ? ordenFlechasHtml + ordenNumHtml : ''}
            </div>
        `;
        }
        
        lista.appendChild(elemento);
        
        // Cargar y renderizar subobjetivos para este objetivo
        if (vistaActual === 'tarjetas') {
            cargarYRenderizarSubobjetivos(obj.id);
        }
    });
    // Evento para el botón Saltar hoy
    document.querySelectorAll('.btn-saltar-hoy, .objetivo-lista-btn.saltar').forEach(btn => {
        btn.addEventListener('click', async function() {
            const objetivoId = this.getAttribute('data-id');
            try {
                const res = await fetch(`/api/objetivos/${objetivoId}/saltar`, { method: 'POST' });
                const result = await res.json();
                if (result.status === 'success') {
                    showSuccess('Objetivo saltado para hoy');
                    await cargarObjetivos();
                } else {
                    showError(result.message || 'No se pudo saltar el objetivo');
                }
            } catch (err) {
                showError('Error al saltar objetivo');
            }
        });
    });
    // Evento para el botón Reactivar hoy
    document.querySelectorAll('.btn-reactivar-hoy, .objetivo-lista-btn.reactivar').forEach(btn => {
        btn.addEventListener('click', async function() {
            const objetivoId = this.getAttribute('data-id');
            try {
                const res = await fetch(`/api/objetivos/${objetivoId}/reactivar_hoy`, { method: 'POST' });
                const result = await res.json();
                if (result.status === 'success') {
                    showSuccess('Objetivo reactivado para hoy');
                    await cargarObjetivos();
                } else {
                    showError(result.message || 'No se pudo reactivar el objetivo');
                }
            } catch (err) {
                showError('Error al reactivar objetivo');
            }
        });
    });

    // Event delegation para toggle de subobjetivos en vista de lista
    document.addEventListener('click', async function(e) {
        const toggleBtn = e.target.closest('.objetivo-lista-btn.toggle-subobjetivos');
        if (!toggleBtn) return;
        
        console.log('Toggle subobjetivos clicked');
        const objetivoId = toggleBtn.getAttribute('data-objetivo-id');
        const subobjetivosContainer = document.getElementById(`subobjetivos-lista-${objetivoId}`);
        const icon = toggleBtn.querySelector('i');
        
        console.log('Objetivo ID:', objetivoId);
        console.log('Container:', subobjetivosContainer);
        
        if (subobjetivosContainer && subobjetivosContainer.style.display === 'none') {
            // Mostrar subobjetivos
            subobjetivosContainer.style.display = 'block';
            icon.className = 'bi bi-chevron-up';
            toggleBtn.classList.add('expanded');
            
            // Cargar subobjetivos si no están cargados
            if (subobjetivosContainer.children.length === 0) {
                await cargarSubobjetivosLista(objetivoId);
            }
        } else if (subobjetivosContainer) {
            // Ocultar subobjetivos
            subobjetivosContainer.style.display = 'none';
            icon.className = 'bi bi-chevron-down';
            toggleBtn.classList.remove('expanded');
        }
    });
    // Eventos para flechas de reordenar objetivos principales
    if (ordenActual === 'orden') {
        document.querySelectorAll('.objetivo-main-up-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                const objetivoId = parseInt(this.getAttribute('data-id'));
                const idx = filtrados.findIndex(obj => obj.id === objetivoId);
                if (idx > 0) {
                    const nuevoOrden = [...filtrados];
                    [nuevoOrden[idx - 1], nuevoOrden[idx]] = [nuevoOrden[idx], nuevoOrden[idx - 1]];
                    try {
                        await fetch('/api/objetivos/reordenar', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                ids: nuevoOrden.map(obj => obj.id),
                                categoria: categoriaActual
                            })
                        });
                        await cargarObjetivos();
                    } catch (err) {
                        showError('Error al reordenar objetivos');
                    }
                }
            });
        });
        document.querySelectorAll('.objetivo-main-down-btn').forEach(btn => {
            btn.addEventListener('click', async function() {
                const objetivoId = parseInt(this.getAttribute('data-id'));
                const idx = filtrados.findIndex(obj => obj.id === objetivoId);
                if (idx < filtrados.length - 1) {
                    const nuevoOrden = [...filtrados];
                    [nuevoOrden[idx], nuevoOrden[idx + 1]] = [nuevoOrden[idx + 1], nuevoOrden[idx]];
                    try {
                        await fetch('/api/objetivos/reordenar', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                ids: nuevoOrden.map(obj => obj.id),
                                categoria: categoriaActual
                            })
                        });
                        await cargarObjetivos();
                    } catch (err) {
                        showError('Error al reordenar objetivos');
                    }
                }
            });
        });
    }
    
    actualizarResumenObjetivos();
}

// --- SUBOBJETIVOS: LÓGICA DE CHECKLIST ---
async function cargarYRenderizarSubobjetivos(objetivoId) {
    const contenedor = document.getElementById(`subobjetivos-list-${objetivoId}`);
    if (!contenedor) return;
    contenedor.innerHTML = '<div class="text-muted small">Cargando checklist...</div>';
    try {
        const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
        let subobjetivos = await res.json();
        contenedor.innerHTML = '';
        if (subobjetivos.length === 0) {
            contenedor.innerHTML = '<div class="text-muted small">No hay subobjetivos.</div>';
        } else {
            // --- NUEVO: mantener array local para UI reactiva ---
            let subobjetivosLocal = [...subobjetivos];
            function renderSubobjetivos() {
                contenedor.innerHTML = '';
                subobjetivosLocal.forEach((sub, idx) => {
                    const subDiv = document.createElement('div');
                    subDiv.className = 'subobjetivo-item';
                    subDiv.innerHTML = `
                        <input type="checkbox" class="subobjetivo-check" data-id="${sub.id}" ${sub.completado ? 'checked' : ''}>
                        <span class="subobjetivo-titulo-span${sub.completado ? ' completado' : ''}">${sub.titulo}</span>
                        <span class="subobjetivo-flex" style="flex:1"></span>
                        <button class="subobjetivo-up-btn" title="Subir" ${idx === 0 ? 'disabled' : ''}>&#8593;</button>
                        <button class="subobjetivo-down-btn" title="Bajar" ${idx === subobjetivosLocal.length - 1 ? 'disabled' : ''}>&#8595;</button>
                        <button class="delete-subobjetivo-btn" data-id="${sub.id}" title="Eliminar">&#10005;</button>
                    `;
                    contenedor.appendChild(subDiv);
                    // Check
                    const chk = subDiv.querySelector('.subobjetivo-check');
                    chk.onchange = async function() {
                        sub.completado = this.checked;
                        renderSubobjetivos();
                        await fetch(`/api/subobjetivos/${sub.id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ completado: sub.completado })
                        });
                    };
                    // Editar (doble click)
                    const tituloSpan = subDiv.querySelector('.subobjetivo-titulo-span');
                    if (tituloSpan) {
                        tituloSpan.ondblclick = function() {
                            const oldText = sub.titulo;
                            const input = document.createElement('input');
                            input.type = 'text';
                            input.value = oldText;
                            input.className = 'subobjetivo-edit-input';
                            input.style.flex = '1 1 0%';
                            this.replaceWith(input);
                            input.focus();
                            input.onblur = async function() {
                                const nuevoTexto = input.value.trim();
                                if (nuevoTexto && nuevoTexto !== oldText) {
                                    sub.titulo = nuevoTexto;
                                    renderSubobjetivos();
                                    await fetch(`/api/subobjetivos/${sub.id}`, {
                                        method: 'PATCH',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ titulo: sub.titulo })
                                    });
                                } else {
                                    renderSubobjetivos();
                                }
                            };
                            input.onkeydown = function(e) { if (e.key === 'Enter') input.blur(); };
                        };
                    }
                    // Subir
                    const upBtn = subDiv.querySelector('.subobjetivo-up-btn');
                    upBtn.onclick = async function() {
                        if (idx > 0) {
                            [subobjetivosLocal[idx - 1], subobjetivosLocal[idx]] = [subobjetivosLocal[idx], subobjetivosLocal[idx - 1]];
                            renderSubobjetivos();
                            const ids = subobjetivosLocal.map(s => s.id);
                            await fetch(`/api/objetivos/${objetivoId}/subobjetivos/reordenar`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ ids })
                            });
                        }
                    };
                    // Bajar
                    const downBtn = subDiv.querySelector('.subobjetivo-down-btn');
                    downBtn.onclick = async function() {
                        if (idx < subobjetivosLocal.length - 1) {
                            [subobjetivosLocal[idx], subobjetivosLocal[idx + 1]] = [subobjetivosLocal[idx + 1], subobjetivosLocal[idx]];
                            renderSubobjetivos();
                            const ids = subobjetivosLocal.map(s => s.id);
                            await fetch(`/api/objetivos/${objetivoId}/subobjetivos/reordenar`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ ids })
                            });
                        }
                    };
                    // Eliminar
                    const delBtn = subDiv.querySelector('.delete-subobjetivo-btn');
                    delBtn.onclick = async function() {
                        subobjetivosLocal.splice(idx, 1);
                        renderSubobjetivos();
                        await fetch(`/api/subobjetivos/${sub.id}`, { method: 'DELETE' });
                    };
                });
            }
            renderSubobjetivos();
        }
    } catch (err) {
        contenedor.innerHTML = '<div class="text-danger small">Error al cargar checklist.</div>';
    }
    // Mostrar/ocultar input para agregar subobjetivo
    const toggleBtn = document.querySelector(`#subobjetivos-container-${objetivoId} .subobjetivo-toggle-btn`);
    const addDiv = document.getElementById(`subobjetivos-add-${objetivoId}`);
    if (toggleBtn && addDiv) {
        toggleBtn.addEventListener('click', function() {
            addDiv.style.display = addDiv.style.display === 'none' ? '' : 'none';
        });
        // Evento para agregar subobjetivo (solo una vez)
        const addBtn = addDiv.querySelector('.subobjetivo-add-btn');
        const input = addDiv.querySelector('.subobjetivo-input');
        if (!addBtn.dataset.listener) {
            addBtn.addEventListener('click', async function() {
                const titulo = input.value.trim();
                if (!titulo) return;
                await agregarSubobjetivo(objetivoId, titulo);
                input.value = '';
            });
            // NUEVO: Permitir agregar con Enter
            input.addEventListener('keydown', async function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const titulo = input.value.trim();
                    if (!titulo) return;
                    await agregarSubobjetivo(objetivoId, titulo);
                    input.value = '';
                }
            });
            addBtn.dataset.listener = 'true';
        }
    }
}

// Tabs de categoría (incluyendo histórico)
document.querySelectorAll('.nav-pills .nav-link[data-periodo]').forEach(tab => {
    tab.addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelectorAll('.nav-pills .nav-link').forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        categoriaActual = this.getAttribute('data-periodo');
        if (categoriaActual === 'historico') {
            document.getElementById('card-objetivos').style.display = 'none';
            document.getElementById('card-historico').style.display = '';
            cargarHistorico();
        } else {
            document.getElementById('card-objetivos').style.display = '';
            document.getElementById('card-historico').style.display = 'none';
            renderObjetivos();
        }
    });
});

// === LÓGICA DE RECURRENCIA SEGÚN CATEGORÍA (ACTUALIZADA) ===
// Ya no se deshabilita el checkbox, solo se usa para decidir si es recurrente
// y la frecuencia se toma de la categoría si está marcado
// Nuevo objetivo
const formNuevo = document.getElementById('form-modal-nuevo-objetivo');
if (formNuevo) {
  formNuevo.addEventListener('submit', async function(e) {
    e.preventDefault();
    const titulo = document.getElementById('modal-titulo-objetivo').value.trim();
    const descripcion = document.getElementById('modal-desc-objetivo').value.trim();
    const prioridad = document.getElementById('modal-prioridad-objetivo').value;
    const categoria = document.getElementById('modal-categoria-objetivo').value;
    const esPadre = document.getElementById('modal-es-padre-objetivo').checked;
    const objetivoPadreId = document.getElementById('modal-padre-objetivo').value || null;
    const estado = document.getElementById('modal-estado-objetivo').value;
    const fechaInicio = document.getElementById('modal-fecha-inicio-objetivo').value || null;
    const fechaFin = document.getElementById('modal-fecha-fin-objetivo').value || null;
    const horas = document.getElementById('modal-horas-estimadas-objetivo').value;
    const minutos = document.getElementById('modal-minutos-estimados-objetivo').value;
    let horasEstimadas = null;
    if (horas || minutos) {
      const h = parseInt(horas) || 0;
      const m = parseInt(minutos) || 0;
      horasEstimadas = h + (m / 60);
    }
    const dificultad = document.getElementById('modal-dificultad-objetivo').value || null;
    const etiquetas = document.getElementById('modal-etiquetas-objetivo').value.trim();
    const recompensa = document.getElementById('modal-recompensa-objetivo').value.trim();
    const notasAdicionales = document.getElementById('modal-notas-adicionales-objetivo').value.trim();
    const chkRecNuevo = document.getElementById('modal-recurrente-objetivo');
    let recurrente = chkRecNuevo.checked;
    let frecuencia = null;
    if (recurrente && ["diario", "semanal", "mensual", "anual"].includes(categoria)) {
      frecuencia = categoria;
    }
    if (!titulo || !categoria) {
      showError('El título y la categoría son obligatorios.');
      return;
    }
    try {
      const res = await fetch('/api/objetivos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titulo,
          descripcion,
          prioridad,
          categoria,
          es_padre: esPadre,
          objetivo_padre_id: objetivoPadreId,
          estado,
          fecha_inicio: fechaInicio,
          fecha_fin: fechaFin,
          horas_estimadas: horasEstimadas,
          dificultad,
          etiquetas,
          recompensa,
          notas_adicionales: notasAdicionales,
          recurrente,
          frecuencia
        })
      });
      const result = await res.json();
      if (result.status === 'success' && result.id) {
        // Guardar subobjetivos si hay
        if (checklistNuevo.length > 0) {
            for (const sub of checklistNuevo) {
                if (sub.titulo.trim()) {
                    await fetch(`/api/objetivos/${result.id}/subobjetivos`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ titulo: sub.titulo, completado: sub.completado })
                    });
                }
            }
        }
        await cargarObjetivos();
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalNuevoObjetivo'));
        if (modal) modal.hide();
        // Cambiar a la pestaña de la categoría si aplica
        const categorias = ['diario', 'semanal', 'mensual', 'anual', 'general'];
        if (categorias.includes(categoria)) {
          const tab = document.querySelector(`.nav-pills .nav-link[data-periodo='${categoria}']`);
          if (tab) tab.click();
        }
      } else {
        showError(result.error || 'Error al crear objetivo');
      }
    } catch (err) {
      showError('Error al crear objetivo');
    }
  });
}
// Editar objetivo
const formEditar = document.getElementById('form-modal-editar-objetivo');
if (formEditar) {
  formEditar.addEventListener('submit', async function(e) {
    e.preventDefault();
    const btnGuardar = document.querySelector('#modalEditarObjetivo .btn-guardar');
    if (btnGuardar) btnGuardar.disabled = true;
    const id = document.getElementById('editar-id-objetivo').value;
    const titulo = document.getElementById('editar-titulo-objetivo').value.trim();
    const descripcion = document.getElementById('editar-desc-objetivo').value.trim();
    const prioridad = document.getElementById('editar-prioridad-objetivo').value;
    const categoria = document.getElementById('editar-categoria-objetivo').value.trim();
    const esPadre = document.getElementById('editar-es-padre-objetivo').checked;
    const objetivoPadreId = document.getElementById('editar-padre-objetivo').value || null;
    const estado = document.getElementById('editar-estado-objetivo').value;
    const fechaInicio = document.getElementById('editar-fecha-inicio-objetivo').value || null;
    const fechaFin = document.getElementById('editar-fecha-fin-objetivo').value || null;
    const horasEdit = document.getElementById('editar-horas-estimadas-objetivo').value;
    const minutosEdit = document.getElementById('editar-minutos-estimados-objetivo').value;
    let horasEstimadas = null;
    if (horasEdit || minutosEdit) {
      const h = parseInt(horasEdit) || 0;
      const m = parseInt(minutosEdit) || 0;
      horasEstimadas = h + (m / 60);
    }
    const dificultad = document.getElementById('editar-dificultad-objetivo').value || null;
    const etiquetas = document.getElementById('editar-etiquetas-objetivo').value.trim();
    const recompensa = document.getElementById('editar-recompensa-objetivo').value.trim();
    const notasAdicionales = document.getElementById('editar-notas-adicionales-objetivo').value.trim();
    const chkRecEdit = document.getElementById('editar-recurrente-objetivo');
    let recurrente = false;
    if (chkRecEdit) {
        recurrente = chkRecEdit.checked;
    }
    let frecuencia = null;
    if (recurrente && ["diario", "semanal", "mensual", "anual"].includes(categoria)) {
      frecuencia = categoria;
    }
    if (!id || !titulo) return;
    try {
      const res = await fetch(`/api/objetivos/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          titulo,
          descripcion,
          prioridad,
          categoria,
          es_padre: esPadre,
          objetivo_padre_id: objetivoPadreId,
          estado,
          fecha_inicio: fechaInicio,
          fecha_fin: fechaFin,
          horas_estimadas: horasEstimadas,
          dificultad,
          etiquetas,
          recompensa,
          notas_adicionales: notasAdicionales,
          recurrente,
          frecuencia
        })
      });
      const result = await res.json();
      if (result.status === 'success') {
        // Sincronizar subobjetivos: crear, actualizar, eliminar
        const objetivoId = id;
        // Obtener subobjetivos actuales del backend
        let backendSubs = [];
        try {
            const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
            backendSubs = await res.json();
        } catch {}
        // Crear nuevos
        for (const sub of checklistEditar) {
            if ((!sub.id || typeof sub.id === 'undefined') && sub.titulo.trim()) {
                await fetch(`/api/objetivos/${objetivoId}/subobjetivos`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ titulo: sub.titulo, completado: sub.completado })
                });
            } else if (sub.id) {
                // Actualizar si cambió
                const backendSub = backendSubs.find(s => s.id === sub.id);
                if (backendSub && (backendSub.titulo !== sub.titulo || backendSub.completado !== sub.completado)) {
                    await fetch(`/api/subobjetivos/${sub.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ titulo: sub.titulo, completado: sub.completado })
                    });
                }
            }
        }
        // Eliminar los que ya no están
        for (const backendSub of backendSubs) {
            if (!checklistEditar.find(s => s.id === backendSub.id)) {
                await fetch(`/api/subobjetivos/${backendSub.id}`, { method: 'DELETE' });
            }
        }
        // Recargar subobjetivos del backend para limpiar duplicados
        try {
            const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
            const subs = await res.json();
            checklistEditar = subs.map(s => ({ id: s.id, titulo: s.titulo, completado: s.completado }));
        } catch {}
        await cargarObjetivos();
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditarObjetivo'));
        if (modal) modal.hide();
      } else {
        showError(result.error || 'Error al actualizar objetivo');
      }
    } catch (err) {
      console.error('Error al actualizar objetivo:', err);
      showError('Error al actualizar objetivo');
    } finally {
      if (btnGuardar) btnGuardar.disabled = false;
    }
  });
}

// Render inicial desde API
if (sessionStorage.getItem('loginReciente') === '1') {
  cargarObjetivos();
  sessionStorage.removeItem('loginReciente');
} else {
  // Intentar cargar solo si hay sesión activa
  fetch('/api/objetivos', { method: 'HEAD' })
    .then(res => {
      if (res.ok) cargarObjetivos();
    });
}
// cargarObjetivos();

// Event listener para el selector de ordenamiento
function inicializarSelectorOrdenamiento() {
    const selectorOrden = document.getElementById('orden-objetivos');
    if (selectorOrden) {
        selectorOrden.addEventListener('change', function() {
            ordenActual = this.value;
            renderObjetivos();
        });
    }

    // Event listeners para cambio de vista
    const vistaRadios = document.querySelectorAll('input[name="vista-objetivos"]');
    vistaRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                vistaActual = this.value;
                renderObjetivos();
            }
        });
    });
}

// Inicializar después de que se carguen los objetivos
setTimeout(inicializarSelectorOrdenamiento, 1000);

// --- Utilidad para poblar el select de objetivo padre ---
async function poblarSelectObjetivoPadre(selectId, objetivoActualId = null) {
    const select = document.getElementById(selectId);
    if (!select) return;
    select.innerHTML = '<option value="">Seleccionar objetivo padre</option>';
    try {
        const res = await fetch('/api/objetivos_padre');
        const objetivosPadre = await res.json();
        objetivosPadre.forEach(obj => {
            if (objetivoActualId && obj.id == objetivoActualId) return; // No permitir ser su propio padre
            const option = document.createElement('option');
            option.value = obj.id;
            option.textContent = obj.titulo;
            select.appendChild(option);
        });
    } catch (err) {
        // Si hay error, dejar solo la opción por defecto
    }
}

// Al abrir el modal de editar objetivo, poblar el select de padre y setear el valor actual
if (formEditar) {
    document.getElementById('modalEditarObjetivo').addEventListener('show.bs.modal', function () {
        const id = document.getElementById('editar-id-objetivo').value;
        poblarSelectObjetivoPadre('editar-padre-objetivo', id);
        // Setear el valor actual del objetivo padre tras poblar el select
        setTimeout(() => {
            const select = document.getElementById('editar-padre-objetivo');
            const padreId = document.getElementById('editar-padre-objetivo').getAttribute('data-valor-padre') || '';
            if (select && padreId) {
                select.value = padreId;
            }
            if (window.objetivoEditandoRecurrente) {
                chkRecEdit.checked = true;
                selFreqEdit.style.display = '';
                selFreqEdit.value = window.objetivoEditandoFrecuencia || 'diario';
            } else {
                chkRecEdit.checked = false;
                selFreqEdit.style.display = 'none';
            }
        }, 200);
    });
}

// === EVENTO PARA ABRIR EL MODAL DE EDITAR OBJETIVO ===
document.addEventListener('click', async function(e) {
    const btn = e.target.closest('.btn-editar, .objetivo-lista-btn.editar');
    if (!btn) return;
    const objetivoId = btn.getAttribute('data-id');
    if (!objetivoId) return;
    // Buscar el objetivo en la lista global
    const objetivo = objetivos.find(obj => obj.id == objetivoId);
    if (!objetivo) return;
    // Setear los valores en el modal de edición
    document.getElementById('editar-id-objetivo').value = objetivo.id;
    document.getElementById('editar-titulo-objetivo').value = objetivo.titulo || '';
    document.getElementById('editar-desc-objetivo').value = objetivo.descripcion || '';
    document.getElementById('editar-prioridad-objetivo').value = objetivo.prioridad || 'media';
    document.getElementById('editar-categoria-objetivo').value = objetivo.categoria || '';
    document.getElementById('editar-es-padre-objetivo').checked = !!objetivo.es_padre;
    document.getElementById('editar-padre-objetivo').value = objetivo.objetivo_padre_id || '';
    document.getElementById('editar-estado-objetivo').value = objetivo.estado || 'pendiente';
    document.getElementById('editar-fecha-inicio-objetivo').value = formatFechaInput(objetivo.fecha_inicio);
    document.getElementById('editar-fecha-fin-objetivo').value = formatFechaInput(objetivo.fecha_fin);
    document.getElementById('editar-horas-estimadas-objetivo').value = objetivo.horas_estimadas ? Math.floor(objetivo.horas_estimadas) : '';
    document.getElementById('editar-minutos-estimados-objetivo').value = objetivo.horas_estimadas ? Math.round((objetivo.horas_estimadas - Math.floor(objetivo.horas_estimadas)) * 60) : '';
    document.getElementById('editar-dificultad-objetivo').value = objetivo.dificultad || '';
    document.getElementById('editar-etiquetas-objetivo').value = objetivo.etiquetas || '';
    document.getElementById('editar-recompensa-objetivo').value = objetivo.recompensa || '';
    document.getElementById('editar-notas-adicionales-objetivo').value = objetivo.notas_adicionales || '';
    document.getElementById('editar-recurrente-objetivo').checked = !!objetivo.recurrente;
    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById('modalEditarObjetivo'));
    modal.show();
    // En el evento de abrir modal de editar, antes de mostrar el modal:
    document.getElementById('editar-padre-objetivo').setAttribute('data-valor-padre', objetivo.objetivo_padre_id || '');
});

function formatFechaInput(fecha) {
    if (!fecha) return '';
    // Si ya es string tipo 'YYYY-MM-DD', úsalo directo
    if (/^\d{4}-\d{2}-\d{2}$/.test(fecha)) return fecha;
    // Si es string tipo 'YYYY-MM-DDTHH:MM:SS', tomar solo la parte de la fecha
    if (typeof fecha === 'string' && fecha.includes('T')) return fecha.split('T')[0];
    // Si es Date o string parseable, formatear a YYYY-MM-DD
    const d = new Date(fecha);
    if (!isNaN(d)) {
        return d.toISOString().split('T')[0];
    }
    return '';
}

function limpiarCamposNuevoObjetivo() {
    document.getElementById('modal-titulo-objetivo').value = '';
    document.getElementById('modal-desc-objetivo').value = '';
    document.getElementById('modal-prioridad-objetivo').value = 'media';
    document.getElementById('modal-categoria-objetivo').value = '';
    document.getElementById('modal-es-padre-objetivo').checked = false;
    document.getElementById('modal-padre-objetivo').value = '';
    document.getElementById('modal-estado-objetivo').value = 'pendiente';
    document.getElementById('modal-fecha-inicio-objetivo').value = '';
    document.getElementById('modal-fecha-fin-objetivo').value = '';
    document.getElementById('modal-horas-estimadas-objetivo').value = '';
    document.getElementById('modal-minutos-estimados-objetivo').value = '';
    document.getElementById('modal-dificultad-objetivo').value = '';
    document.getElementById('modal-etiquetas-objetivo').value = '';
    document.getElementById('modal-recompensa-objetivo').value = '';
    document.getElementById('modal-notas-adicionales-objetivo').value = '';
    document.getElementById('modal-recurrente-objetivo').checked = false;
}

document.addEventListener('click', async function(e) {
    const btnEliminar = e.target.closest('.btn-eliminar, .objetivo-lista-btn.eliminar');
    if (btnEliminar) {
        const objetivoId = btnEliminar.getAttribute('data-id');
        if (!objetivoId) return;
        showConfirm('¿Estás seguro de que deseas eliminar este objetivo? Esta acción no se puede deshacer.').then(async (result) => {
            if (result.isConfirmed) {
                try {
                    const res = await fetch(`/api/objetivos/${objetivoId}`, {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const result = await res.json();
                    if (result.status === 'success') {
                        showSuccess('Objetivo eliminado correctamente.');
                        await cargarObjetivos();
                    } else {
                        showError(result.error || 'Error al eliminar objetivo');
                    }
                } catch (err) {
                    showError('Error al eliminar objetivo');
                }
            }
        });
    }
});

function formatearHorasMinutos(valor) {
  if (!valor) return '';
  const horas = Math.floor(valor);
  const minutos = Math.round((valor - horas) * 60);
  let res = '';
  if (horas > 0) res += `${horas}h`;
  if (minutos > 0) res += (horas > 0 ? ' ' : '') + `${minutos}m`;
  if (!res) res = '0h';
  return res;
}

document.addEventListener('change', async function(e) {
    const checkbox = e.target.closest('.check-objetivo');
    if (!checkbox) return;
    const objetivoId = checkbox.getAttribute('data-id');
    if (!objetivoId) return;
    try {
        await fetch(`/api/objetivos/${objetivoId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completado: checkbox.checked })
        });
        await cargarObjetivos();
    } catch (err) {
        showError('Error al actualizar el objetivo');
    }
});

document.getElementById('btn-deseleccionar-recurrentes')?.addEventListener('click', async function() {
    const recurrentesMarcados = objetivos.filter(obj => obj.recurrente && obj.completado && !es_objetivo_vencido_front(obj));
    if (recurrentesMarcados.length === 0) {
        showInfo('No hay objetivos recurrentes marcados para desmarcar.');
        return;
    }
    for (const obj of recurrentesMarcados) {
        await fetch(`/api/objetivos/${obj.id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completado: false })
        });
    }
    await cargarObjetivos();
    showSuccess('Todos los objetivos recurrentes han sido desmarcados.');
});

function es_objetivo_vencido_front(obj) {
    // Lógica similar a backend para saber si el objetivo ya está vencido
    if (!obj) return false;
    const hoy = new Date();
    if (obj.fecha_fin) {
        return new Date(obj.fecha_fin) < hoy;
    }
    if (obj.recurrente && obj.frecuencia && obj.fecha_inicio) {
        const inicio = new Date(obj.fecha_inicio);
        let vencimiento = null;
        switch (obj.frecuencia) {
            case 'diario': vencimiento = new Date(inicio); vencimiento.setDate(inicio.getDate() + 1); break;
            case 'semanal': vencimiento = new Date(inicio); vencimiento.setDate(inicio.getDate() + 7); break;
            case 'mensual': vencimiento = new Date(inicio); vencimiento.setDate(inicio.getDate() + 30); break;
            case 'anual': vencimiento = new Date(inicio); vencimiento.setFullYear(inicio.getFullYear() + 1); break;
        }
        return vencimiento && hoy > vencimiento;
    }
    if (!obj.recurrente && obj.categoria && obj.fecha_creacion) {
        const creacion = new Date(obj.fecha_creacion);
        switch (obj.categoria) {
            case 'diario': return hoy > creacion;
            case 'semanal': { let v = new Date(creacion); v.setDate(creacion.getDate() + 7); return hoy > v; }
            case 'mensual': { let v = new Date(creacion); v.setDate(creacion.getDate() + 30); return hoy > v; }
        }
    }
    return false;
}

const modalNuevo = document.getElementById('modalNuevoObjetivo');
if (modalNuevo) {
    modalNuevo.addEventListener('show.bs.modal', function () {
        poblarSelectObjetivoPadre('modal-padre-objetivo');
        });
    }
});

// Inicializa los eventos de administración de preguntas (editar, eliminar, switches, etc)
function initAdminEvents() {
    // Re-inicializar eventos de editar, eliminar, switches, etc.
    // Eliminar pregunta
    document.querySelectorAll('.delete-question').forEach(btn => {
        btn.onclick = function(e) {
            e.preventDefault();
            const id = this.dataset.id;
            showConfirm('¿Estás seguro de que deseas eliminar esta pregunta? Se eliminarán también todas las respuestas asociadas. Esta acción no se puede deshacer.').then((result) => {
                if (result.isConfirmed) {
                    fetch(`/question/${id}`, {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
                    })
                    .then(res => res.json())
                    .then(res => {
                        if (res.status === 'success') {
                            this.closest('.pregunta-item').remove();
                            showSuccess('Pregunta eliminada correctamente.');
                        } else {
                            showError('Error al eliminar: ' + (res.message || ''));
                        }
                    })
                    .catch(err => showError('Error al eliminar: ' + err));
                }
            });
        };
    });
    // Puedes agregar aquí la reinicialización de otros eventos (editar, switches, etc.)
}

function limpiarHistorico() {
    historico = [];
    historicoOffset = 0;
    historicoFin = false;
    document.getElementById('lista-historico').innerHTML = '';
}

async function cargarHistorico(mas = false) {
    if (!mas) {
        limpiarHistorico();
    }
    if (historicoFin) return;
    const tipo = document.getElementById('filtro-tipo-historico').value;
    const estado = document.getElementById('filtro-estado-historico').value;
    const fecha_inicio = document.getElementById('filtro-fecha-inicio-historico').value;
    const fecha_fin = document.getElementById('filtro-fecha-fin-historico').value;
    const q = document.getElementById('filtro-busqueda-historico').value.trim();
    let url = `/api/objetivos_historico?limit=${historicoLimit}&offset=${historicoOffset}`;
    if (tipo) url += `&tipo=${tipo}`;
    if (estado) url += `&estado=${estado}`;
    if (fecha_inicio) url += `&fecha_inicio=${fecha_inicio}`;
    if (fecha_fin) url += `&fecha_fin=${fecha_fin}`;
    if (q) url += `&q=${encodeURIComponent(q)}`;
    try {
        const res = await fetch(url);
        const data = await res.json();
        if (Array.isArray(data)) {
            // Evitar duplicados por id
            const idsExistentes = new Set(historico.map(obj => obj.id));
            const nuevos = data.filter(obj => !idsExistentes.has(obj.id));
            historico = historico.concat(nuevos);
            historicoOffset += historicoLimit;
            if (data.length < historicoLimit) historicoFin = true;
            renderHistorico();
        }
    } catch (err) {
        showError('Error al cargar histórico');
    }
}

function renderHistorico() {
    const lista = document.getElementById('lista-historico');
    lista.innerHTML = '';
    if (historico.length === 0) {
        lista.innerHTML = '<li class="list-group-item text-center text-muted">No hay objetivos históricos para los filtros seleccionados.</li>';
        return;
    }
    historico.forEach(obj => {
        const fechaFin = obj.fecha_fin ? new Date(obj.fecha_fin + 'T12:00:00').toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' }) : '';
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex align-items-center';
        const tituloClass = obj.completado ? 'objetivo-titulo flex-grow-1 text-decoration-line-through' : 'objetivo-titulo flex-grow-1';
        const etiqueta = obj.completado
            ? '<span class="badge bg-success ms-2">Completado</span>'
            : '<span class="badge bg-danger ms-2">No cumplido</span>';
        // Botón más pequeño, solo ícono
        const btnReactivar = !obj.recurrente ? `<button class="btn btn-xs btn-outline-primary p-1 ms-2 btn-reactivar-recurrente" data-id="${obj.id}" title="Marcar como recurrente" style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;"><i class="bi bi-arrow-repeat"></i></button>` : '';
        li.innerHTML = `
            <span class="${tituloClass}">${obj.titulo}</span>
            ${etiqueta}
            ${fechaFin ? `<span class="badge bg-light text-dark ms-auto"><i class='bi bi-calendar-check'></i> ${fechaFin}</span>` : ''}
            ${btnReactivar}
        `;
        lista.appendChild(li);
    });
    // Eventos para reactivar como recurrente
    lista.querySelectorAll('.btn-reactivar-recurrente').forEach(btn => {
        btn.onclick = async function() {
            const id = this.getAttribute('data-id');
            try {
                const res = await fetch(`/api/objetivos/${id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ recurrente: true })
                });
                const result = await res.json();
                if (result.status === 'success') {
                    showSuccess('Objetivo marcado como recurrente');
                    // Eliminar de históricos en memoria
                    const idx = historico.findIndex(o => o.id == id);
                    if (idx !== -1) {
                        historico.splice(idx, 1);
                    }
                    renderHistorico();
                    // Recargar la lista de activos y contadores desde el backend
                    await cargarObjetivos();
                } else {
                    showError(result.error || 'Error al marcar como recurrente');
                }
            } catch (err) {
                showError('Error de red al marcar como recurrente');
            }
        };
    });
    document.getElementById('btn-cargar-mas-historico').style.display = historicoFin ? 'none' : 'inline-block';
}

// Eventos de pestañas y filtros para histórico
const tabHist = document.getElementById('tab-historico');
const cardHist = document.getElementById('card-historico');
if (tabHist && cardHist) {
    tabHist.addEventListener('click', function(e) {
        e.preventDefault();
        document.getElementById('card-objetivos').style.display = 'none';
        cardHist.style.display = '';
        cargarHistorico();
    });
}
['filtro-tipo-historico','filtro-estado-historico','filtro-fecha-inicio-historico','filtro-fecha-fin-historico','filtro-busqueda-historico'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener('change', function() {
            cargarHistorico();
        });
        if (id === 'filtro-busqueda-historico') {
            el.addEventListener('keyup', function(e) {
                if (e.key === 'Enter') cargarHistorico();
            });
        }
    }
});
const btnMas = document.getElementById('btn-cargar-mas-historico');
if (btnMas) {
    btnMas.addEventListener('click', function() {
        cargarHistorico(true);
    });
}

// === CHECKLIST DE SUBOBJETIVOS EN MODALES ===
// --- NUEVO OBJETIVO ---
let checklistNuevo = [];
function renderChecklistNuevo() {
    const list = document.getElementById('checklist-nuevo-list');
    if (!list) return;
    list.innerHTML = '';
    if (checklistNuevo.length === 0) {
        list.innerHTML = '<div class="text-muted small">No hay subobjetivos.</div>';
        return;
    }
    checklistNuevo.forEach((sub, idx) => {
        const div = document.createElement('div');
        div.className = 'd-flex align-items-center mb-1';
        div.innerHTML = `
            <input type="checkbox" class="form-check-input me-2" ${sub.completado ? 'checked' : ''} data-idx="${idx}">
            <input type="text" class="form-control form-control-sm me-2" value="${sub.titulo}" data-idx="${idx}" ${sub.completado ? 'style=\'text-decoration:line-through;color:#888;\'' : ''}>
            <button class="btn btn-sm btn-outline-secondary me-1 subobjetivo-up-btn" data-idx="${idx}" ${idx === 0 ? 'disabled' : ''} title="Subir">&#8593;</button>
            <button class="btn btn-sm btn-outline-secondary me-1 subobjetivo-down-btn" data-idx="${idx}" ${idx === checklistNuevo.length - 1 ? 'disabled' : ''} title="Bajar">&#8595;</button>
            <button class="btn btn-sm btn-outline-danger" data-idx="${idx}"><i class="bi bi-x"></i></button>
        `;
        list.appendChild(div);
    });
    // Eventos
    list.querySelectorAll('input[type=checkbox]').forEach(chk => {
        chk.onchange = function() {
            const idx = this.getAttribute('data-idx');
            checklistNuevo[idx].completado = this.checked;
            renderChecklistNuevo();
        };
    });
    list.querySelectorAll('input[type=text]').forEach(input => {
        input.onblur = function() {
            const idx = this.getAttribute('data-idx');
            checklistNuevo[idx].titulo = this.value;
            renderChecklistNuevo();
        };
    });
    list.querySelectorAll('button.btn-outline-danger').forEach(btn => {
        btn.onclick = function() {
            const idx = this.getAttribute('data-idx');
            checklistNuevo.splice(idx, 1);
            renderChecklistNuevo();
        };
    });
    // Subir/bajar
    list.querySelectorAll('button.subobjetivo-up-btn').forEach(btn => {
        btn.onclick = function() {
            const idx = parseInt(this.getAttribute('data-idx'));
            if (idx > 0) {
                [checklistNuevo[idx - 1], checklistNuevo[idx]] = [checklistNuevo[idx], checklistNuevo[idx - 1]];
                renderChecklistNuevo();
            }
        };
    });
    list.querySelectorAll('button.subobjetivo-down-btn').forEach(btn => {
        btn.onclick = function() {
            const idx = parseInt(this.getAttribute('data-idx'));
            if (idx < checklistNuevo.length - 1) {
                [checklistNuevo[idx], checklistNuevo[idx + 1]] = [checklistNuevo[idx + 1], checklistNuevo[idx]];
                renderChecklistNuevo();
            }
        };
    });
}
document.getElementById('btn-toggle-checklist-nuevo')?.addEventListener('click', function() {
    const cont = document.getElementById('checklist-nuevo-container');
    cont.style.display = cont.style.display === 'none' ? '' : 'none';
});
document.getElementById('checklist-nuevo-add-btn')?.addEventListener('click', function() {
    const input = document.getElementById('checklist-nuevo-input');
    const titulo = input.value.trim();
    if (!titulo) return;
    checklistNuevo.push({ titulo, completado: false });
    input.value = '';
    renderChecklistNuevo();
});
// Limpiar checklist al abrir modal nuevo
const modalNuevo = document.getElementById('modalNuevoObjetivo');
if (modalNuevo) {
    modalNuevo.addEventListener('show.bs.modal', function() {
        checklistNuevo = [];
        renderChecklistNuevo();
        document.getElementById('checklist-nuevo-input').value = '';
        document.getElementById('checklist-nuevo-container').style.display = 'none';
    });
}
// --- EDITAR OBJETIVO ---
let checklistEditar = [];
function renderChecklistEditar() {
    const list = document.getElementById('checklist-editar-list');
    if (!list) return;
    list.innerHTML = '';
    if (checklistEditar.length === 0) {
        list.innerHTML = '<div class="text-muted small">No hay subobjetivos.</div>';
        return;
    }
    checklistEditar.forEach((sub, idx) => {
        const div = document.createElement('div');
        div.className = 'd-flex align-items-center mb-1 subobjetivo-item';
        div.innerHTML = `
            <input type="checkbox" class="form-check-input me-2" ${sub.completado ? 'checked' : ''} data-idx="${idx}">
            <textarea class="form-control form-control-sm me-2 subobjetivo-textarea" data-idx="${idx}" rows="1" style="overflow:hidden;resize:none;">${sub.titulo}</textarea>
            <button class="btn btn-sm btn-outline-secondary me-1 subobjetivo-up-btn" data-idx="${idx}" ${idx === 0 ? 'disabled' : ''} title="Subir">&#8593;</button>
            <button class="btn btn-sm btn-outline-secondary me-1 subobjetivo-down-btn" data-idx="${idx}" ${idx === checklistEditar.length - 1 ? 'disabled' : ''} title="Bajar">&#8595;</button>
            <button class="btn btn-sm btn-outline-danger" data-idx="${idx}"><i class="bi bi-x"></i></button>
        `;
        list.appendChild(div);
    });
    // Eventos
    list.querySelectorAll('input[type=checkbox]').forEach(chk => {
        chk.onchange = function() {
            const idx = this.getAttribute('data-idx');
            checklistEditar[idx].completado = this.checked;
            renderChecklistEditar();
        };
    });
    list.querySelectorAll('textarea').forEach(textarea => {
        // Autoajustar altura
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
        textarea.oninput = function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
            const idx = this.getAttribute('data-idx');
            checklistEditar[idx].titulo = this.value;
        };
        textarea.onblur = function() {
            const idx = this.getAttribute('data-idx');
            checklistEditar[idx].titulo = this.value;
            renderChecklistEditar();
        };
    });
    list.querySelectorAll('button.btn-outline-danger').forEach(btn => {
        btn.onclick = function() {
            const idx = this.getAttribute('data-idx');
            checklistEditar.splice(idx, 1);
            renderChecklistEditar();
        };
    });
    // Subir/bajar
    list.querySelectorAll('button.subobjetivo-up-btn').forEach(btn => {
        btn.onclick = function() {
            const idx = parseInt(this.getAttribute('data-idx'));
            if (idx > 0) {
                [checklistEditar[idx - 1], checklistEditar[idx]] = [checklistEditar[idx], checklistEditar[idx - 1]];
                renderChecklistEditar();
            }
        };
    });
    list.querySelectorAll('button.subobjetivo-down-btn').forEach(btn => {
        btn.onclick = function() {
            const idx = parseInt(this.getAttribute('data-idx'));
            if (idx < checklistEditar.length - 1) {
                [checklistEditar[idx], checklistEditar[idx + 1]] = [checklistEditar[idx + 1], checklistEditar[idx]];
                renderChecklistEditar();
            }
        };
    });
}
document.getElementById('btn-toggle-checklist-editar')?.addEventListener('click', function() {
    const cont = document.getElementById('checklist-editar-container');
    cont.style.display = cont.style.display === 'none' ? '' : 'none';
});
document.getElementById('checklist-editar-add-btn')?.addEventListener('click', function() {
    const input = document.getElementById('checklist-editar-input');
    const titulo = input.value.trim();
    if (!titulo) return;
    checklistEditar.push({ titulo, completado: false });
    input.value = '';
    renderChecklistEditar();
});
// Al abrir modal editar, cargar subobjetivos del backend
const modalEditar = document.getElementById('modalEditarObjetivo');
if (modalEditar) {
    modalEditar.addEventListener('show.bs.modal', async function() {
        const objetivoId = document.getElementById('editar-id-objetivo').value;
        checklistEditar = [];
        if (objetivoId) {
            try {
                const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
                const subs = await res.json();
                checklistEditar = subs.map(s => ({ id: s.id, titulo: s.titulo, completado: s.completado }));
            } catch {}
        }
        renderChecklistEditar();
        document.getElementById('checklist-editar-input').value = '';
        // Fuerza visibilidad del checklist de subobjetivos
        const checklistCont = document.getElementById('checklist-editar-container');
        if (checklistCont) checklistCont.style.display = '';
    });
}
// --- GUARDAR SUBOBJETIVOS AL EDITAR ---
const formEditar = document.getElementById('form-modal-editar-objetivo');
if (formEditar) {
    formEditar.addEventListener('submit', async function(e) {
        e.preventDefault();
        const btnGuardar = document.querySelector('#modalEditarObjetivo .btn-guardar');
        if (btnGuardar) btnGuardar.disabled = true;
        const id = document.getElementById('editar-id-objetivo').value;
        const titulo = document.getElementById('editar-titulo-objetivo').value.trim();
        const descripcion = document.getElementById('editar-desc-objetivo').value.trim();
        const prioridad = document.getElementById('editar-prioridad-objetivo').value;
        const categoria = document.getElementById('editar-categoria-objetivo').value.trim();
        const esPadre = document.getElementById('editar-es-padre-objetivo').checked;
        const objetivoPadreId = document.getElementById('editar-padre-objetivo').value || null;
        const estado = document.getElementById('editar-estado-objetivo').value;
        const fechaInicio = document.getElementById('editar-fecha-inicio-objetivo').value || null;
        const fechaFin = document.getElementById('editar-fecha-fin-objetivo').value || null;
        const horasEdit = document.getElementById('editar-horas-estimadas-objetivo').value;
        const minutosEdit = document.getElementById('editar-minutos-estimados-objetivo').value;
        let horasEstimadas = null;
        if (horasEdit || minutosEdit) {
          const h = parseInt(horasEdit) || 0;
          const m = parseInt(minutosEdit) || 0;
          horasEstimadas = h + (m / 60);
        }
        const dificultad = document.getElementById('editar-dificultad-objetivo').value || null;
        const etiquetas = document.getElementById('editar-etiquetas-objetivo').value.trim();
        const recompensa = document.getElementById('editar-recompensa-objetivo').value.trim();
        const notasAdicionales = document.getElementById('editar-notas-adicionales-objetivo').value.trim();
        const chkRecEdit = document.getElementById('editar-recurrente-objetivo');
        let recurrente = false;
        if (chkRecEdit) {
            recurrente = chkRecEdit.checked;
        }
        let frecuencia = null;
        if (recurrente && ["diario", "semanal", "mensual", "anual"].includes(categoria)) {
          frecuencia = categoria;
        }
        if (!id || !titulo) return;
        try {
          const res = await fetch(`/api/objetivos/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              titulo,
              descripcion,
              prioridad,
              categoria,
              es_padre: esPadre,
              objetivo_padre_id: objetivoPadreId,
              estado,
              fecha_inicio: fechaInicio,
              fecha_fin: fechaFin,
              horas_estimadas: horasEstimadas,
              dificultad,
              etiquetas,
              recompensa,
              notas_adicionales: notasAdicionales,
              recurrente,
              frecuencia
            })
          });
          const result = await res.json();
          if (result.status === 'success') {
            // Sincronizar subobjetivos: crear, actualizar, eliminar
            const objetivoId = id;
            // Obtener subobjetivos actuales del backend
            let backendSubs = [];
            try {
                const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
                backendSubs = await res.json();
            } catch {}
            // Crear nuevos
            for (const sub of checklistEditar) {
                if ((!sub.id || typeof sub.id === 'undefined') && sub.titulo.trim()) {
                    await fetch(`/api/objetivos/${objetivoId}/subobjetivos`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ titulo: sub.titulo, completado: sub.completado })
                    });
                } else if (sub.id) {
                    // Actualizar si cambió
                    const backendSub = backendSubs.find(s => s.id === sub.id);
                    if (backendSub && (backendSub.titulo !== sub.titulo || backendSub.completado !== sub.completado)) {
                        await fetch(`/api/subobjetivos/${sub.id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ titulo: sub.titulo, completado: sub.completado })
                        });
                    }
                }
            }
            // Eliminar los que ya no están
            for (const backendSub of backendSubs) {
                if (!checklistEditar.find(s => s.id === backendSub.id)) {
                    await fetch(`/api/subobjetivos/${backendSub.id}`, { method: 'DELETE' });
                }
            }
            // Recargar subobjetivos del backend para limpiar duplicados
            try {
                const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
                const subs = await res.json();
                checklistEditar = subs.map(s => ({ id: s.id, titulo: s.titulo, completado: s.completado }));
            } catch {}
            await cargarObjetivos();
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditarObjetivo'));
            if (modal) modal.hide();
          } else {
            showError(result.error || 'Error al actualizar objetivo');
          }
        } catch (err) {
          console.error('Error al actualizar objetivo:', err);
          showError('Error al actualizar objetivo');
        } finally {
          if (btnGuardar) btnGuardar.disabled = false;
        }
    });
}

// --- FUNCIÓN PARA AGREGAR SUBOBJETIVO EN VISTA PRINCIPAL ---
async function agregarSubobjetivo(objetivoId, texto) {
    try {
        console.log('[AgregarSubobjetivo] Enviando POST:', texto);
        const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ titulo: texto })
        });
        const postResult = await res.json();
        console.log('[AgregarSubobjetivo] Respuesta POST:', postResult);
        if (!res.ok) {
            showNotification(postResult.error || 'Error al agregar subobjetivo', 'danger');
            return;
        }
        // Polling inteligente: intenta hasta 3 veces obtener la lista con el nuevo subobjetivo
        let subobjetivos = [];
        let encontrado = false;
        for (let intento = 1; intento <= 3; intento++) {
            const res2 = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
            subobjetivos = await res2.json();
            console.log(`[AgregarSubobjetivo] Lista tras agregar (intento ${intento}):`, subobjetivos);
            if (Array.isArray(subobjetivos) && subobjetivos.some(s => s.titulo === texto)) {
                encontrado = true;
                break;
            }
            await new Promise(r => setTimeout(r, 200));
        }
        if (!encontrado) {
            showNotification('Advertencia: El subobjetivo puede tardar en aparecer. Intenta recargar si no lo ves.', 'warning');
        }
        // Renderizado inline de la lista de subobjetivos
        const contenedor = document.getElementById(`subobjetivos-list-${objetivoId}`);
        if (contenedor) {
            contenedor.innerHTML = '';
            if (subobjetivos.length === 0) {
                contenedor.innerHTML = '<div class="text-muted small">No hay subobjetivos.</div>';
            } else {
                subobjetivos.forEach((sub, idx) => {
                    const subDiv = document.createElement('div');
                    subDiv.className = 'subobjetivo-item';
                    subDiv.innerHTML = `
                        <input type="checkbox" class="subobjetivo-check" data-id="${sub.id}" ${sub.completado ? 'checked' : ''}>
                        <span class="subobjetivo-titulo-span${sub.completado ? ' completado' : ''}">${sub.titulo}</span>
                        <span class="subobjetivo-flex" style="flex:1"></span>
                        <button class="subobjetivo-up-btn" title="Subir" ${idx === 0 ? 'disabled' : ''}>&#8593;</button>
                        <button class="subobjetivo-down-btn" title="Bajar" ${idx === subobjetivos.length - 1 ? 'disabled' : ''}>&#8595;</button>
                        <button class="delete-subobjetivo-btn" data-id="${sub.id}" title="Eliminar">&#10005;</button>
                    `;
                    contenedor.appendChild(subDiv);
                    // Check
                    const chk = subDiv.querySelector('.subobjetivo-check');
                    chk.onchange = async function() {
                        sub.completado = this.checked;
                        await fetch(`/api/subobjetivos/${sub.id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ completado: sub.completado })
                        });
                        // Renderiza de nuevo tras actualizar
                        agregarSubobjetivo(objetivoId, ''); // Solo para refrescar la lista
                    };
                    // Editar (doble click)
                    const tituloSpan = subDiv.querySelector('.subobjetivo-titulo-span');
                    if (tituloSpan) {
                        tituloSpan.ondblclick = function() {
                            const oldText = sub.titulo;
                            const input = document.createElement('input');
                            input.type = 'text';
                            input.value = oldText;
                            input.className = 'subobjetivo-edit-input';
                            input.style.flex = '1 1 0%';
                            this.replaceWith(input);
                            input.focus();
                            input.onblur = async function() {
                                const nuevoTexto = input.value.trim();
                                if (nuevoTexto && nuevoTexto !== oldText) {
                                    sub.titulo = nuevoTexto;
                                    await fetch(`/api/subobjetivos/${sub.id}`, {
                                        method: 'PATCH',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ titulo: sub.titulo })
                                    });
                                }
                                // Renderiza de nuevo tras editar
                                agregarSubobjetivo(objetivoId, '');
                            };
                            input.onkeydown = function(e) { if (e.key === 'Enter') input.blur(); };
                        };
                    }
                    // Subir
                    const upBtn = subDiv.querySelector('.subobjetivo-up-btn');
                    upBtn.onclick = async function() {
                        if (idx > 0) {
                            // Intercambia en el array local y reordena en backend
                            [subobjetivos[idx - 1], subobjetivos[idx]] = [subobjetivos[idx], subobjetivos[idx - 1]];
                            const ids = subobjetivos.map(s => s.id);
                            await fetch(`/api/objetivos/${objetivoId}/subobjetivos/reordenar`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ ids })
                            });
                            agregarSubobjetivo(objetivoId, '');
                        }
                    };
                    // Bajar
                    const downBtn = subDiv.querySelector('.subobjetivo-down-btn');
                    downBtn.onclick = async function() {
                        if (idx < subobjetivos.length - 1) {
                            [subobjetivos[idx], subobjetivos[idx + 1]] = [subobjetivos[idx + 1], subobjetivos[idx]];
                            const ids = subobjetivos.map(s => s.id);
                            await fetch(`/api/objetivos/${objetivoId}/subobjetivos/reordenar`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ ids })
                            });
                            agregarSubobjetivo(objetivoId, '');
                        }
                    };
                    // Eliminar
                    const delBtn = subDiv.querySelector('.delete-subobjetivo-btn');
                    delBtn.onclick = async function() {
                        await fetch(`/api/subobjetivos/${sub.id}`, { method: 'DELETE' });
                        agregarSubobjetivo(objetivoId, '');
                    };
                });
            }
        }
        // Limpia el input solo tras éxito
        const addDiv = document.getElementById(`subobjetivos-add-${objetivoId}`);
        if (addDiv) {
            const input = addDiv.querySelector('.subobjetivo-input');
            const addBtn = addDiv.querySelector('.subobjetivo-add-btn');
            if (input) input.value = '';
            if (addBtn) addBtn.disabled = false;
        }
    } catch (err) {
        showNotification('Error al agregar subobjetivo: ' + (err.message || err), 'danger');
        console.error('[AgregarSubobjetivo] Error:', err);
    }
}



// Función para renderizar la lista de subobjetivos
function renderSubobjetivosList(objetivoId, subobjetivos) {
    const contenedor = document.getElementById(`subobjetivos-list-${objetivoId}`);
    if (!contenedor) return;
    contenedor.innerHTML = '';
    if (!Array.isArray(subobjetivos) || subobjetivos.length === 0) {
        contenedor.innerHTML = '<div class="text-muted small">No hay subobjetivos.</div>';
        return;
    }
    subobjetivos.forEach((sub, idx) => {
        const subDiv = document.createElement('div');
        subDiv.className = 'subobjetivo-item';
        subDiv.innerHTML = `
            <input type="checkbox" class="subobjetivo-check" data-id="${sub.id}" ${sub.completado ? 'checked' : ''}>
            <span class="subobjetivo-titulo-span${sub.completado ? ' completado' : ''}">${sub.titulo}</span>
            <span class="subobjetivo-flex" style="flex:1"></span>
            <button class="subobjetivo-up-btn" title="Subir" ${idx === 0 ? 'disabled' : ''}>&#8593;</button>
            <button class="subobjetivo-down-btn" title="Bajar" ${idx === subobjetivos.length - 1 ? 'disabled' : ''}>&#8595;</button>
            <button class="delete-subobjetivo-btn" data-id="${sub.id}" title="Eliminar">&#10005;</button>
        `;
        contenedor.appendChild(subDiv);
        // Check
        const chk = subDiv.querySelector('.subobjetivo-check');
        chk.onchange = async function() {
            sub.completado = this.checked;
            await fetch(`/api/subobjetivos/${sub.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ completado: sub.completado })
            });
            // Refresca la lista tras actualizar
            await fetchAndRenderSubobjetivos(objetivoId);
        };
        // Editar (doble click)
        const tituloSpan = subDiv.querySelector('.subobjetivo-titulo-span');
        if (tituloSpan) {
            tituloSpan.ondblclick = function() {
                const oldText = sub.titulo;
                const input = document.createElement('input');
                input.type = 'text';
                input.value = oldText;
                input.className = 'subobjetivo-edit-input';
                input.style.flex = '1 1 0%';
                this.replaceWith(input);
                input.focus();
                input.onblur = async function() {
                    const nuevoTexto = input.value.trim();
                    if (nuevoTexto && nuevoTexto !== oldText) {
                        sub.titulo = nuevoTexto;
                        await fetch(`/api/subobjetivos/${sub.id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ titulo: sub.titulo })
                        });
                    }
                    await fetchAndRenderSubobjetivos(objetivoId);
                };
                input.onkeydown = function(e) { if (e.key === 'Enter') input.blur(); };
            };
        }
        // Subir
        const upBtn = subDiv.querySelector('.subobjetivo-up-btn');
        upBtn.onclick = async function() {
            if (idx > 0) {
                [subobjetivos[idx - 1], subobjetivos[idx]] = [subobjetivos[idx], subobjetivos[idx - 1]];
                const ids = subobjetivos.map(s => s.id);
                await fetch(`/api/objetivos/${objetivoId}/subobjetivos/reordenar`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids })
                });
                await fetchAndRenderSubobjetivos(objetivoId);
            }
        };
        // Bajar
        const downBtn = subDiv.querySelector('.subobjetivo-down-btn');
        downBtn.onclick = async function() {
            if (idx < subobjetivos.length - 1) {
                [subobjetivos[idx], subobjetivos[idx + 1]] = [subobjetivos[idx + 1], subobjetivos[idx]];
                const ids = subobjetivos.map(s => s.id);
                await fetch(`/api/objetivos/${objetivoId}/subobjetivos/reordenar`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids })
                });
                await fetchAndRenderSubobjetivos(objetivoId);
            }
        };
        // Eliminar
        const delBtn = subDiv.querySelector('.delete-subobjetivo-btn');
        delBtn.onclick = async function() {
            await fetch(`/api/subobjetivos/${sub.id}`, { method: 'DELETE' });
            await fetchAndRenderSubobjetivos(objetivoId);
        };
    });
}

// Función para hacer fetch y renderizar subobjetivos
async function fetchAndRenderSubobjetivos(objetivoId) {
    const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
    const subobjetivos = await res.json();
    renderSubobjetivosList(objetivoId, subobjetivos);
}

// Refactor de agregarSubobjetivo
async function agregarSubobjetivo(objetivoId, texto) {
    try {
        console.log('[AgregarSubobjetivo] Enviando POST:', texto);
        const res = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ titulo: texto })
        });
        const postResult = await res.json();
        console.log('[AgregarSubobjetivo] Respuesta POST:', postResult);
        if (!res.ok) {
            showNotification(postResult.error || 'Error al agregar subobjetivo', 'danger');
            return;
        }
        // Polling inteligente: intenta hasta 3 veces obtener la lista con el nuevo subobjetivo
        let subobjetivos = [];
        let encontrado = false;
        for (let intento = 1; intento <= 3; intento++) {
            const res2 = await fetch(`/api/objetivos/${objetivoId}/subobjetivos`);
            subobjetivos = await res2.json();
            console.log(`[AgregarSubobjetivo] Lista tras agregar (intento ${intento}):`, subobjetivos);
            if (Array.isArray(subobjetivos) && subobjetivos.some(s => s.titulo === texto)) {
                encontrado = true;
                break;
            }
            await new Promise(r => setTimeout(r, 200));
        }
        if (!encontrado) {
            showNotification('Advertencia: El subobjetivo puede tardar en aparecer. Intenta recargar si no lo ves.', 'warning');
        }
        renderSubobjetivosList(objetivoId, subobjetivos);
        // Limpia el input solo tras éxito
        const addDiv = document.getElementById(`subobjetivos-add-${objetivoId}`);
        if (addDiv) {
            const input = addDiv.querySelector('.subobjetivo-input');
            const addBtn = addDiv.querySelector('.subobjetivo-add-btn');
            if (input) input.value = '';
            if (addBtn) addBtn.disabled = false;
        }
    } catch (err) {
        showNotification('Error al agregar subobjetivo: ' + (err.message || err), 'danger');
        console.error('[AgregarSubobjetivo] Error:', err);
    }
}
// === SISTEMA DE FRASES INSPIRACIONALES ===

// Cargar frases desde el backend
async function cargarFrases() {
    try {
        const response = await fetch('/api/frases');
        frases = await response.json();
        renderizarFrases();
        actualizarEstadisticasFrases();
    } catch (error) {
        console.error('Error cargando frases:', error);
        showError('Error al cargar las frases');
    }
}

// Renderizar lista de frases
function renderizarFrases() {
    const lista = document.getElementById('lista-frases');
    const mensajeSin = document.getElementById('mensaje-sin-frases');
    const filtroCategoria = document.getElementById('filtro-categoria-frases')?.value || '';
    
    if (!lista) return;
    
    // Actualizar texto del botón "Repasar Todas" según el filtro
    const btnRepasarTodas = document.getElementById('btn-repasar-todas');
    if (btnRepasarTodas) {
        if (filtroCategoria) {
            btnRepasarTodas.innerHTML = `<i class="bi bi-arrow-repeat me-1"></i>Repasar ${capitalizarPrimeraLetra(filtroCategoria)}`;
        } else {
            btnRepasarTodas.innerHTML = `<i class="bi bi-arrow-repeat me-1"></i>Repasar Todas`;
        }
    }
    
    // Filtrar frases por categoría
    const frasesFiltradas = filtroCategoria ? 
        frases.filter(f => f.categoria === filtroCategoria) : frases;
    
    if (frasesFiltradas.length === 0) {
        lista.innerHTML = '';
        if (mensajeSin) mensajeSin.style.display = 'block';
        return;
    }
    
    if (mensajeSin) mensajeSin.style.display = 'none';
    
    lista.innerHTML = frasesFiltradas.map(frase => {
        const esRepasadaHoy = esRepasadaHoyFrase(frase.ultima_vez);
        const totalRepasos = frase.total_repasos || 0;
        
        return `
            <div class="frase-card ${esRepasadaHoy ? 'repasada-hoy' : ''}">
                <div class="frase-texto">${frase.texto}</div>
                ${frase.autor ? `<div class="frase-autor">${frase.autor}</div>` : ''}
                
                <div class="frase-meta">
                    <div class="d-flex align-items-center gap-2">
                        <span class="frase-categoria ${frase.categoria}">
                            <i class="bi bi-tag"></i>
                            ${capitalizarPrimeraLetra(frase.categoria)}
                        </span>
                        <div class="frase-estadisticas">
                            <div class="frase-contador">
                                <i class="bi bi-arrow-repeat"></i>
                                <span>${totalRepasos} repasos</span>
                            </div>
                            ${frase.ultima_vez ? `<div class="frase-ultima-vez">Último: ${formatearFechaRelativa(frase.ultima_vez)}</div>` : ''}
                        </div>
                    </div>
                    
                    <div class="frase-acciones">
                        <button class="frase-btn repasar" onclick="repasarFrase(${frase.id})" title="Repasar frase">
                            <i class="bi bi-eye"></i>
                            ${esRepasadaHoy ? 'Repasada' : 'Repasar'}
                        </button>
                        <button class="frase-btn editar" onclick="editarFrase(${frase.id})" title="Editar">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="frase-btn eliminar" onclick="eliminarFrase(${frase.id})" title="Eliminar">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
                
                ${frase.notas ? `<div class="frase-notas">${frase.notas}</div>` : ''}
            </div>
        `;
    }).join('');
}

// Actualizar estadísticas de frases
function actualizarEstadisticasFrases() {
    const totalFrases = document.getElementById('total-frases');
    const frasesHoy = document.getElementById('frases-hoy');
    const frasesSemana = document.getElementById('frases-semana');
    const totalRepasos = document.getElementById('total-repasos');
    
    if (!totalFrases) return;
    
    const hoy = new Date();
    const inicioSemana = new Date(hoy);
    inicioSemana.setDate(hoy.getDate() - hoy.getDay());
    
    const repasadasHoy = frases.filter(f => esRepasadaHoyFrase(f.ultima_vez)).length;
    const repasadasSemana = frases.filter(f => {
        if (!f.ultima_vez) return false;
        const fecha = new Date(f.ultima_vez);
        return fecha >= inicioSemana;
    }).length;
    const sumaRepasos = frases.reduce((sum, f) => sum + (f.total_repasos || 0), 0);
    
    totalFrases.textContent = frases.length;
    frasesHoy.textContent = repasadasHoy;
    frasesSemana.textContent = repasadasSemana;
    totalRepasos.textContent = sumaRepasos;
}

// Verificar si una frase fue repasada hoy
function esRepasadaHoyFrase(ultimaVez) {
    if (!ultimaVez) return false;
    const hoy = new Date().toDateString();
    const fechaUltima = new Date(ultimaVez).toDateString();
    return hoy === fechaUltima;
}

// Repasar una frase (incrementar contador)
async function repasarFrase(fraseId) {
    try {
        const response = await fetch(`/api/frases/${fraseId}/repasar`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showSuccess('¡Frase repasada!');
            await cargarFrases();
        } else {
            showError('Error al repasar la frase');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error al repasar la frase');
    }
}

// Repasar todas las frases - Iniciar sesión de repaso
async function repasarTodasLasFrases() {
    if (frases.length === 0) {
        showInfo('No tienes frases para repasar');
        return;
    }
    
    // Obtener filtro de categoría actual
    const filtroCategoria = document.getElementById('filtro-categoria-frases')?.value || '';
    
    // Filtrar frases según la categoría seleccionada
    let frasesParaRepasar;
    if (filtroCategoria) {
        frasesParaRepasar = frases.filter(f => f.categoria === filtroCategoria);
        if (frasesParaRepasar.length === 0) {
            showInfo(`No tienes frases de la categoría "${capitalizarPrimeraLetra(filtroCategoria)}" para repasar`);
            return;
        }
    } else {
        frasesParaRepasar = frases;
    }
    
    // Iniciar sesión de repaso con las frases filtradas
    iniciarSesionRepaso(frasesParaRepasar, filtroCategoria);
}

// Iniciar sesión de repaso
function iniciarSesionRepaso(frasesParaRepasar = frases, categoriaFiltro = '') {
    // Preparar frases para repaso (mezclar aleatoriamente)
    sesionRepaso.frases = [...frasesParaRepasar].sort(() => Math.random() - 0.5);
    sesionRepaso.indiceActual = 0;
    sesionRepaso.frasesRepasadas = 0;
    sesionRepaso.activa = true;
    sesionRepaso.categoriaFiltro = categoriaFiltro; // Guardar la categoría filtrada
    
    // Ocultar la interfaz principal de frases
    document.getElementById('card-frases').style.display = 'none';
    
    // Mostrar la interfaz de repaso
    mostrarInterfazRepaso();
    
    // Mostrar la primera frase
    mostrarFraseRepaso();
}

// Mostrar interfaz de repaso
function mostrarInterfazRepaso() {
    const cardFrases = document.getElementById('card-frases');
    const interfazRepaso = document.createElement('div');
    interfazRepaso.id = 'interfaz-repaso';
    interfazRepaso.className = 'card mt-3';
    interfazRepaso.innerHTML = `
        <div class="card-body">
            <!-- Header de repaso -->
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h5 class="mb-1"><i class="bi bi-arrow-repeat"></i> Sesión de Repaso</h5>
                    <p class="text-muted mb-0">
                        ${sesionRepaso.categoriaFiltro ? 
                            `Repasando frases de: <span class="frase-categoria ${sesionRepaso.categoriaFiltro}">${capitalizarPrimeraLetra(sesionRepaso.categoriaFiltro)}</span>` : 
                            'Repasando todas tus frases inspiracionales'
                        }
                    </p>
                </div>
                <button class="btn btn-outline-secondary" onclick="terminarSesionRepaso()">
                    <i class="bi bi-x"></i> Terminar
                </button>
            </div>
            
            <!-- Barra de progreso -->
            <div class="progress-container mb-4">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="fw-semibold">Progreso</span>
                    <span id="progreso-repaso">1 de ${sesionRepaso.frases.length}</span>
                </div>
                <div class="progress">
                    <div class="progress-bar" id="barra-progreso-repaso" role="progressbar" 
                         style="width: ${(1 / sesionRepaso.frases.length * 100)}%;" 
                         aria-valuenow="1" aria-valuemin="0" aria-valuemax="${sesionRepaso.frases.length}">
                    </div>
                </div>
            </div>
            
            <!-- Contenedor de frase -->
            <div id="contenedor-frase-repaso" class="text-center py-5">
                <!-- La frase se cargará aquí -->
            </div>
            
            <!-- Controles de repaso -->
            <div class="d-flex justify-content-center gap-3 mt-4">
                <button class="btn btn-outline-secondary" id="btn-anterior-repaso" onclick="fraseAnterior()" disabled>
                    <i class="bi bi-chevron-left"></i> Anterior
                </button>
                <button class="btn btn-success" id="btn-repasada" onclick="marcarRepasadaYSiguiente()">
                    <i class="bi bi-check-circle"></i> Repasada
                </button>
                <button class="btn btn-primary" id="btn-siguiente-repaso" onclick="siguienteFrase()">
                    Siguiente <i class="bi bi-chevron-right"></i>
                </button>
            </div>
            
            <!-- Estadísticas de sesión -->
            <div class="row text-center mt-4 pt-3 border-top">
                <div class="col-4">
                    <div class="h5 mb-0 text-success" id="frases-repasadas-sesion">0</div>
                    <small class="text-muted">Repasadas</small>
                </div>
                <div class="col-4">
                    <div class="h5 mb-0 text-primary" id="frases-restantes-sesion">${sesionRepaso.frases.length}</div>
                    <small class="text-muted">Restantes</small>
                </div>
                <div class="col-4">
                    <div class="h5 mb-0 text-info" id="tiempo-sesion">00:00</div>
                    <small class="text-muted">Tiempo</small>
                </div>
            </div>
        </div>
    `;
    
    // Insertar después del card de frases
    cardFrases.parentNode.insertBefore(interfazRepaso, cardFrases.nextSibling);
    
    // Iniciar cronómetro de sesión
    iniciarCronometroSesion();
}

// Mostrar frase actual en la sesión de repaso
function mostrarFraseRepaso() {
    const frase = sesionRepaso.frases[sesionRepaso.indiceActual];
    const contenedor = document.getElementById('contenedor-frase-repaso');
    
    if (!frase) {
        finalizarSesionRepaso();
        return;
    }
    
    contenedor.innerHTML = `
        <div class="frase-repaso-card">
            <div class="frase-texto-repaso mb-4" style="font-size: 1.5rem; color: #1f2937; line-height: 1.6;">
                "${frase.texto}"
            </div>
            ${frase.autor ? `<div class="frase-autor-repaso mb-3" style="font-size: 1.1rem; color: #6b7280;">— ${frase.autor}</div>` : ''}
            <div class="d-flex justify-content-center gap-2 mb-3">
                <span class="frase-categoria ${frase.categoria}" style="font-size: 0.9rem;">
                    <i class="bi bi-tag"></i>
                    ${capitalizarPrimeraLetra(frase.categoria)}
                </span>
            </div>
            ${frase.notas ? `<div class="frase-notas-repaso mt-3 p-3 bg-light rounded" style="font-style: italic; color: #6b7280;">${frase.notas}</div>` : ''}
        </div>
    `;
    
    // Actualizar controles
    actualizarControlesRepaso();
}

// Actualizar controles de repaso
function actualizarControlesRepaso() {
    const btnAnterior = document.getElementById('btn-anterior-repaso');
    const btnSiguiente = document.getElementById('btn-siguiente-repaso');
    const progreso = document.getElementById('progreso-repaso');
    const barraProgreso = document.getElementById('barra-progreso-repaso');
    
    // Actualizar botones
    btnAnterior.disabled = sesionRepaso.indiceActual === 0;
    
    if (sesionRepaso.indiceActual === sesionRepaso.frases.length - 1) {
        btnSiguiente.innerHTML = '<i class="bi bi-check-circle"></i> Finalizar';
        btnSiguiente.className = 'btn btn-success';
    } else {
        btnSiguiente.innerHTML = 'Siguiente <i class="bi bi-chevron-right"></i>';
        btnSiguiente.className = 'btn btn-primary';
    }
    
    // Actualizar progreso
    const actual = sesionRepaso.indiceActual + 1;
    const total = sesionRepaso.frases.length;
    progreso.textContent = `${actual} de ${total}`;
    barraProgreso.style.width = `${(actual / total * 100)}%`;
    barraProgreso.setAttribute('aria-valuenow', actual);
}

// Marcar frase como repasada y continuar
async function marcarRepasadaYSiguiente() {
    const frase = sesionRepaso.frases[sesionRepaso.indiceActual];
    
    try {
        const response = await fetch(`/api/frases/${frase.id}/repasar`, {
            method: 'POST'
        });
        
        if (response.ok) {
            sesionRepaso.frasesRepasadas++;
            actualizarEstadisticasSesion();
            
            // Mostrar feedback visual
            const btnRepasada = document.getElementById('btn-repasada');
            const textoOriginal = btnRepasada.innerHTML;
            btnRepasada.innerHTML = '<i class="bi bi-check-circle-fill"></i> ¡Repasada!';
            btnRepasada.className = 'btn btn-success';
            btnRepasada.disabled = true;
            
            setTimeout(() => {
                btnRepasada.innerHTML = textoOriginal;
                btnRepasada.className = 'btn btn-success';
                btnRepasada.disabled = false;
                siguienteFrase();
            }, 800);
        } else {
            showError('Error al marcar la frase como repasada');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error al marcar la frase como repasada');
    }
}

// Ir a la siguiente frase
function siguienteFrase() {
    if (sesionRepaso.indiceActual < sesionRepaso.frases.length - 1) {
        sesionRepaso.indiceActual++;
        mostrarFraseRepaso();
    } else {
        finalizarSesionRepaso();
    }
}

// Ir a la frase anterior
function fraseAnterior() {
    if (sesionRepaso.indiceActual > 0) {
        sesionRepaso.indiceActual--;
        mostrarFraseRepaso();
    }
}

// Actualizar estadísticas de la sesión
function actualizarEstadisticasSesion() {
    const repasadas = document.getElementById('frases-repasadas-sesion');
    const restantes = document.getElementById('frases-restantes-sesion');
    
    if (repasadas) repasadas.textContent = sesionRepaso.frasesRepasadas;
    if (restantes) restantes.textContent = sesionRepaso.frases.length - sesionRepaso.frasesRepasadas;
}

function iniciarCronometroSesion() {
    cronometroSesion.inicio = new Date();
    cronometroSesion.intervalo = setInterval(() => {
        const ahora = new Date();
        const transcurrido = Math.floor((ahora - cronometroSesion.inicio) / 1000);
        const minutos = Math.floor(transcurrido / 60);
        const segundos = transcurrido % 60;
        
        const tiempoElement = document.getElementById('tiempo-sesion');
        if (tiempoElement) {
            tiempoElement.textContent = `${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

// Finalizar sesión de repaso
function finalizarSesionRepaso() {
    // Detener cronómetro
    if (cronometroSesion.intervalo) {
        clearInterval(cronometroSesion.intervalo);
    }
    
    const tiempoTotal = cronometroSesion.inicio ? 
        Math.floor((new Date() - cronometroSesion.inicio) / 1000) : 0;
    const minutos = Math.floor(tiempoTotal / 60);
    const segundos = tiempoTotal % 60;
    
    // Mostrar resumen
    const tituloCategoria = sesionRepaso.categoriaFiltro ? 
        `¡Sesión de ${capitalizarPrimeraLetra(sesionRepaso.categoriaFiltro)} Completada!` : 
        '¡Sesión Completada!';
    
    const descripcionCategoria = sesionRepaso.categoriaFiltro ? 
        `<div class="mb-3"><span class="frase-categoria ${sesionRepaso.categoriaFiltro}"><i class="bi bi-tag"></i> ${capitalizarPrimeraLetra(sesionRepaso.categoriaFiltro)}</span></div>` : 
        '';
    
    Swal.fire({
        title: tituloCategoria,
        html: `
            <div class="text-center">
                <div class="mb-3">
                    <i class="bi bi-check-circle-fill text-success" style="font-size: 4rem;"></i>
                </div>
                ${descripcionCategoria}
                <div class="row">
                    <div class="col-4">
                        <div class="h4 text-success">${sesionRepaso.frasesRepasadas}</div>
                        <small class="text-muted">Frases repasadas</small>
                    </div>
                    <div class="col-4">
                        <div class="h4 text-primary">${sesionRepaso.frases.length}</div>
                        <small class="text-muted">Total de frases</small>
                    </div>
                    <div class="col-4">
                        <div class="h4 text-info">${minutos}:${segundos.toString().padStart(2, '0')}</div>
                        <small class="text-muted">Tiempo total</small>
                    </div>
                </div>
            </div>
        `,
        icon: null,
        confirmButtonText: 'Continuar',
        allowOutsideClick: false
    }).then(() => {
        terminarSesionRepaso();
    });
}

// Terminar sesión de repaso
function terminarSesionRepaso() {
    // Limpiar cronómetro
    if (cronometroSesion.intervalo) {
        clearInterval(cronometroSesion.intervalo);
    }
    
    // Remover interfaz de repaso
    const interfazRepaso = document.getElementById('interfaz-repaso');
    if (interfazRepaso) {
        interfazRepaso.remove();
    }
    
    // Mostrar interfaz principal de frases
    document.getElementById('card-frases').style.display = 'block';
    
    // Resetear sesión
    sesionRepaso.activa = false;
    sesionRepaso.categoriaFiltro = '';
    
    // Recargar frases para actualizar estadísticas
    cargarFrases();
}

// Hacer funciones globales para los controles
window.marcarRepasadaYSiguiente = marcarRepasadaYSiguiente;
window.siguienteFrase = siguienteFrase;
window.fraseAnterior = fraseAnterior;
window.terminarSesionRepaso = terminarSesionRepaso;

// Mostrar frase aleatoria
async function mostrarFraseAleatoria() {
    if (frases.length === 0) {
        showInfo('No tienes frases agregadas');
        return;
    }
    
    const fraseAleatoria = frases[Math.floor(Math.random() * frases.length)];
    
    const html = `
        <div class="text-center">
            <div class="frase-texto mb-3" style="font-size: 1.3rem; color: #1f2937;">
                "${fraseAleatoria.texto}"
            </div>
            ${fraseAleatoria.autor ? `<div class="frase-autor mb-3">— ${fraseAleatoria.autor}</div>` : ''}
            <div class="d-flex justify-content-center gap-2">
                <span class="frase-categoria ${fraseAleatoria.categoria}">
                    ${capitalizarPrimeraLetra(fraseAleatoria.categoria)}
                </span>
            </div>
        </div>
    `;
    
    Swal.fire({
        title: 'Frase del Momento',
        html: html,
        icon: null,
        showCancelButton: true,
        confirmButtonText: 'Repasar',
        cancelButtonText: 'Cerrar',
        customClass: {
            popup: 'swal-wide'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            repasarFrase(fraseAleatoria.id);
        }
    });
}

// Editar frase
function editarFrase(fraseId) {
    const frase = frases.find(f => f.id === fraseId);
    if (!frase) return;
    
    document.getElementById('editar-frase-id').value = frase.id;
    document.getElementById('editar-frase-texto').value = frase.texto;
    document.getElementById('editar-frase-autor').value = frase.autor || '';
    document.getElementById('editar-frase-categoria').value = frase.categoria;
    document.getElementById('editar-frase-notas').value = frase.notas || '';
    
    const modal = new bootstrap.Modal(document.getElementById('modalEditarFrase'));
    modal.show();
}

// Eliminar frase
async function eliminarFrase(fraseId) {
    const result = await Swal.fire({
        title: '¿Eliminar frase?',
        text: 'Esta acción no se puede deshacer',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc2626',
        cancelButtonColor: '#6b7280',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar'
    });
    
    if (result.isConfirmed) {
        try {
            const response = await fetch(`/api/frases/${fraseId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showSuccess('Frase eliminada');
                await cargarFrases();
            } else {
                showError('Error al eliminar la frase');
            }
        } catch (error) {
            console.error('Error:', error);
            showError('Error al eliminar la frase');
        }
    }
}

// Funciones auxiliares
function capitalizarPrimeraLetra(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatearFechaRelativa(fecha) {
    const ahora = new Date();
    const fechaObj = new Date(fecha);
    const diffMs = ahora - fechaObj;
    const diffDias = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDias === 0) return 'Hoy';
    if (diffDias === 1) return 'Ayer';
    if (diffDias < 7) return `Hace ${diffDias} días`;
    if (diffDias < 30) return `Hace ${Math.floor(diffDias / 7)} semanas`;
    return fechaObj.toLocaleDateString();
}

// Función para configurar event listeners de frases
function configurarEventListenersFrases() {
    // Botón nueva frase
    const btnNuevaFrase = document.getElementById('btn-nueva-frase');
    if (btnNuevaFrase && !btnNuevaFrase.hasAttribute('data-listener-added')) {
        btnNuevaFrase.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('modalNuevaFrase'));
            modal.show();
        });
        btnNuevaFrase.setAttribute('data-listener-added', 'true');
    }
    
    // Botón repasar todas
    const btnRepasarTodas = document.getElementById('btn-repasar-todas');
    if (btnRepasarTodas) {
        btnRepasarTodas.addEventListener('click', repasarTodasLasFrases);
    }
    
    // Botón frase aleatoria
    const btnFraseAleatoria = document.getElementById('btn-frase-aleatoria');
    if (btnFraseAleatoria && !btnFraseAleatoria.hasAttribute('data-listener-added')) {
        btnFraseAleatoria.addEventListener('click', mostrarFraseAleatoria);
        btnFraseAleatoria.setAttribute('data-listener-added', 'true');
    }
    
    // Filtro de categoría
    const filtroCategoria = document.getElementById('filtro-categoria-frases');
    if (filtroCategoria && !filtroCategoria.hasAttribute('data-listener-added')) {
        filtroCategoria.addEventListener('change', renderizarFrases);
        filtroCategoria.setAttribute('data-listener-added', 'true');
    }
    
    // Form nueva frase
    const formNuevaFrase = document.getElementById('form-nueva-frase');
    if (formNuevaFrase && !formNuevaFrase.hasAttribute('data-listener-added')) {
        formNuevaFrase.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const datos = {
                texto: document.getElementById('frase-texto').value,
                autor: document.getElementById('frase-autor').value,
                categoria: document.getElementById('frase-categoria').value,
                notas: document.getElementById('frase-notas').value
            };
            
            try {
                const response = await fetch('/api/frases', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(datos)
                });
                
                if (response.ok) {
                    showSuccess('Frase agregada exitosamente');
                    bootstrap.Modal.getInstance(document.getElementById('modalNuevaFrase')).hide();
                    formNuevaFrase.reset();
                    await cargarFrases();
                } else {
                    showError('Error al agregar la frase');
                }
            } catch (error) {
                console.error('Error:', error);
                showError('Error al agregar la frase');
            }
        });
        formNuevaFrase.setAttribute('data-listener-added', 'true');
    }
    
    // Form editar frase
    const formEditarFrase = document.getElementById('form-editar-frase');
    if (formEditarFrase && !formEditarFrase.hasAttribute('data-listener-added')) {
        formEditarFrase.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fraseId = document.getElementById('editar-frase-id').value;
            const datos = {
                texto: document.getElementById('editar-frase-texto').value,
                autor: document.getElementById('editar-frase-autor').value,
                categoria: document.getElementById('editar-frase-categoria').value,
                notas: document.getElementById('editar-frase-notas').value
            };
            
            try {
                const response = await fetch(`/api/frases/${fraseId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(datos)
                });
                
                if (response.ok) {
                    showSuccess('Frase actualizada exitosamente');
                    bootstrap.Modal.getInstance(document.getElementById('modalEditarFrase')).hide();
                    await cargarFrases();
                } else {
                    showError('Error al actualizar la frase');
                }
            } catch (error) {
                console.error('Error:', error);
                showError('Error al actualizar la frase');
            }
        });
        formEditarFrase.setAttribute('data-listener-added', 'true');
    }
}

// Event listeners para frases
document.addEventListener('DOMContentLoaded', function() {
    // Configurar event listeners iniciales
    configurarEventListenersFrases();
});

// Hacer funciones globales
window.repasarFrase = repasarFrase;
window.editarFrase = editarFrase;
window.eliminarFrase = eliminarFrase;
window.cargarFrases = cargarFrases;
window.configurarEventListenersFrases = configurarEventListenersFrases;