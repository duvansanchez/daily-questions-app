console.log('JS CARGADO');

// Variables globales
let currentQuestionIndex = 0;
let questions = [];
let responses = {};
let questionTimers = {}; // Para almacenar los timers de cada pregunta
let questionStartTimes = {}; // Para almacenar los tiempos de inicio

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
function showNotification(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.main-container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
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

// Función para enviar las respuestas al servidor
async function submitResponses() {
    try {
        console.log('Respuestas que se enviarán:', responses);
        
        // Obtener la fecha seleccionada del dropdown
        const fechaSelect = document.getElementById('fecha-respuesta-select');
        let fechaParaEnviar;
        
        if (fechaSelect && fechaSelect.value === 'ayer') {
            // Si seleccionó "Ayer", calcular la fecha de ayer
            const ayer = new Date();
            ayer.setDate(ayer.getDate() - 1);
            fechaParaEnviar = ayer.toISOString().split('T')[0];
        } else {
            // Por defecto usar hoy
            fechaParaEnviar = new Date().toISOString().split('T')[0];
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
    // Definir las variables necesarias para el handler
    const bloqueCatExistenteNueva = document.getElementById('bloque-categoria-existente-nueva');
    const bloqueNuevaCatNueva = document.getElementById('bloque-nueva-categoria-nueva');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Submit capturado'); // Para depuración
            // Validar existencia de los bloques
            if (!bloqueCatExistenteNueva || !bloqueNuevaCatNueva) {
                console.error('No se encontraron los bloques de categoría.');
                return;
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
    async function fetchFrecuenciaDatos(preguntaId, periodo) {
        try {
            const response = await fetch(`/api/stats/frequency/${preguntaId}?periodo=${periodo}`, {
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
        const selectedOption = preguntaSelector.options[preguntaSelector.selectedIndex];
        const tipo = selectedOption.getAttribute('data-tipo');
        const periodo = document.querySelector('.periodo-btn.active').getAttribute('data-periodo');
        const tipoGrafico = document.querySelector('.tipo-grafico-btn.active').getAttribute('data-tipo');
        periodoTitulo.textContent = periodo;

        // Limpiar estado anterior
        graficoFrecuencia.innerHTML = '';
        mensajeExclusion.classList.add('d-none');

        if (esTextoAbierto(tipo)) {
            mensajeExclusion.classList.remove('d-none');
            return;
        }

        try {
            // Mostrar indicador de carga
            graficoFrecuencia.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><div class="mt-2">Cargando datos...</div></div>';
            
            // Obtener datos reales
            const datos = await fetchFrecuenciaDatos(selectedOption.value, periodo);
            
            // Verificar si hay datos
            if (!datos.labels || datos.labels.length === 0) {
                graficoFrecuencia.innerHTML = '<div class="text-center py-5 text-muted">No hay datos disponibles para esta pregunta en el período seleccionado.</div>';
                return;
            }
            
            // Renderizar gráfico
            renderGrafico(datos, tipoGrafico);
            
            // Actualizar título del gráfico con información específica
            const tituloElement = document.querySelector('#graficoFrecuencia').closest('.card').querySelector('h5');
            if (tituloElement) {
                let titulo = `Frecuencia por ${periodo}`;
                if (datos.question_type) {
                    if (['radio', 'checkbox'].includes(datos.question_type)) {
                        titulo = `Distribución de opciones seleccionadas`;
                        } else if (['yes_no', 'boolean'].includes(datos.question_type) || (datos.labels && datos.labels.length === 2 && datos.labels.includes('Sí') && datos.labels.includes('No'))) {
                            titulo = `Frecuencia de respuestas Sí/No`;
                    }
                }
                tituloElement.textContent = titulo;
            }
            
        } catch (error) {
            console.error('Error en actualizarFrecuencia:', error);
            
            if (error.message === 'excluded') {
                mensajeExclusion.classList.remove('d-none');
            } else {
                graficoFrecuencia.innerHTML = `
                    <div class="text-center py-5">
                        <div class="text-danger mb-2">
                            <i class="bi bi-exclamation-triangle"></i>
                        </div>
                        <div class="text-muted">Error al cargar los datos: ${error.message}</div>
                    </div>
                `;
            }
        }
    }

    // Eventos
    preguntaSelector.addEventListener('change', actualizarFrecuencia);
    periodoBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            periodoBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            actualizarFrecuencia();
        });
    });
    tipoGraficoBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            tipoGraficoBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            actualizarFrecuencia();
        });
    });

    // Inicializar al cargar el tab
    if (preguntaSelector) {
        actualizarFrecuencia();
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

    // === HISTÓRICO DE OBJETIVOS ===
    let historico = [];
    let historicoOffset = 0;
    let historicoLimit = 20;
    let historicoFin = false;

    function limpiarHistorico() {
        historico = [];
        historicoOffset = 0;
        historicoFin = false;
        document.getElementById('lista-historico').innerHTML = '';
    }

    async function cargarHistorico(mas = false) {
        if (!mas) limpiarHistorico();
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
                historico = historico.concat(data);
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
            // Formateo de fechas en español
            const fechaCreacion = obj.fecha_creacion ? new Date(obj.fecha_creacion + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
            const fechaInicio = obj.fecha_inicio ? new Date(obj.fecha_inicio + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
            const fechaFin = obj.fecha_fin ? new Date(obj.fecha_fin + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex align-items-center';
            if (obj.completado) li.classList.add('objetivo-completado');
            li.innerHTML = `
                <div style="flex:1;min-width:0;">
                    <input type="checkbox" class="form-check-input me-2 check-objetivo" ${obj.completado ? 'checked' : ''} data-id="${obj.id}">
                    <span class="objetivo-titulo">${obj.titulo}</span>
                    <span class="etiqueta-prioridad ${obj.prioridad}">${obj.prioridad.charAt(0).toUpperCase() + obj.prioridad.slice(1)}</span>
                    ${obj.categoria ? `<span class="etiqueta-categoria">${obj.categoria.charAt(0).toUpperCase() + obj.categoria.slice(1)}</span>` : ''}
                    ${obj.estado ? `<span class="badge bg-secondary ms-1">${obj.estado.replace('_', ' ').toUpperCase()}</span>` : ''}
                    ${obj.descripcion ? `<div class="objetivo-desc">${obj.descripcion}</div>` : ''}
                    <div class="objetivo-extra mt-1 small text-muted">
                        ${fechaCreacion ? `<span class="objetivo-fecha"><i class='bi bi-calendar-plus'></i> Creado: ${fechaCreacion}</span>` : ''}
                        ${obj.recompensa ? `<span class="objetivo-recompensa"><i class='bi bi-gift'></i> ${obj.recompensa}</span>` : ''}
                        ${fechaInicio ? `<span class="objetivo-fecha"><i class='bi bi-calendar-event'></i> Inicio: ${fechaInicio}</span>` : ''}
                        ${fechaFin ? `<span class="objetivo-fecha"><i class='bi bi-calendar-check'></i> Fin: ${fechaFin}</span>` : ''}
                        ${obj.horas_estimadas ? `<span class="objetivo-horas"><i class='bi bi-clock'></i> ${obj.horas_estimadas}h</span>` : ''}
                        ${obj.dificultad ? `<span class="objetivo-dificultad"><i class='bi bi-bar-chart'></i> Dificultad: ${obj.dificultad}</span>` : ''}
                        ${obj.etiquetas ? `<span class="objetivo-etiquetas"><i class='bi bi-tags'></i> ${obj.etiquetas}</span>` : ''}
                    </div>
                    ${obj.notas_adicionales ? `<div class="objetivo-notas small text-info mt-1"><i class='bi bi-info-circle'></i> ${obj.notas_adicionales}</div>` : ''}
                </div>
                <div class="acciones-objetivo">
                    <button class="btn-editar" title="Editar" data-id="${obj.id}"><i class="bi bi-pencil"></i></button>
                    <button class="btn-eliminar" title="Eliminar" data-id="${obj.id}"><i class="bi bi-trash"></i></button>
                </div>
            `;
            lista.appendChild(li);
        });
        document.getElementById('btn-cargar-mas-historico').style.display = historicoFin ? 'none' : 'inline-block';
    }

    // Eventos de pestañas y filtros
    const tabObj = document.getElementById('tab-objetivos');
    const tabHist = document.getElementById('tab-historico');
    const cardObj = document.getElementById('card-objetivos');
    const cardHist = document.getElementById('card-historico');
    if (tabObj && tabHist && cardObj && cardHist) {
        tabObj.addEventListener('click', function(e) {
            e.preventDefault();
            tabObj.classList.add('active');
            tabHist.classList.remove('active');
            cardObj.style.display = '';
            cardHist.style.display = 'none';
        });
        tabHist.addEventListener('click', function(e) {
            e.preventDefault();
            tabHist.classList.add('active');
            tabObj.classList.remove('active');
            cardObj.style.display = 'none';
            cardHist.style.display = '';
            cargarHistorico();
        });
    }
    // Filtros histórico
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
    // Botón cargar más
    const btnMas = document.getElementById('btn-cargar-mas-historico');
    if (btnMas) {
        btnMas.addEventListener('click', function() {
            cargarHistorico(true);
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

// === Objetivos Desarrollo Personal (Integración API) ===
let objetivos = [];
let categoriaActual = 'todos';

async function cargarObjetivos() {
    try {
        const res = await fetch('/api/objetivos');
        objetivos = await res.json();
        renderObjetivos();
    } catch (err) {
        objetivos = [];
        renderObjetivos();
        showError('Error al cargar objetivos');
    }
}

function actualizarResumenObjetivos() {
    // Filtrar por categoría
    const categorias = ['diario', 'semanal', 'mensual', 'anual'];
    // Objetivos diarios: mostrar completados/total
    const diarios = objetivos.filter(obj => (obj.categoria || 'diario') === 'diario');
    const diariosCompletados = diarios.filter(obj => obj.completado).length;
    const elDiarios = document.getElementById('objetivos-diarios');
    if (elDiarios) {
        elDiarios.textContent = `${diariosCompletados}/${diarios.length}`;
    }
    // Progreso semanal
    const semanales = objetivos.filter(obj => (obj.categoria || 'diario') === 'semanal');
    const semanalesCompletados = semanales.filter(obj => obj.completado).length;
    const progresoSemanal = semanales.length > 0 ? Math.round((semanalesCompletados / semanales.length) * 100) : 0;
    const elSemanal = document.getElementById('progreso-semanal');
    if (elSemanal) {
        elSemanal.textContent = `${progresoSemanal}%`;
    }
    // Progreso mensual
    const mensuales = objetivos.filter(obj => (obj.categoria || 'diario') === 'mensual');
    const mensualesCompletados = mensuales.filter(obj => obj.completado).length;
    const progresoMensual = mensuales.length > 0 ? Math.round((mensualesCompletados / mensuales.length) * 100) : 0;
    const elMensual = document.getElementById('progreso-mensual');
    if (elMensual) {
        elMensual.textContent = `${progresoMensual}%`;
    }
    // Progreso anual
    const anuales = objetivos.filter(obj => (obj.categoria || 'diario') === 'anual');
    const anualesCompletados = anuales.filter(obj => obj.completado).length;
    const progresoAnual = anuales.length > 0 ? Math.round((anualesCompletados / anuales.length) * 100) : 0;
    const elAnual = document.getElementById('progreso-anual');
    if (elAnual) {
        elAnual.textContent = `${progresoAnual}%`;
    }
}

function renderObjetivos() {
    const lista = document.getElementById('lista-objetivos');
    lista.innerHTML = '';
    let filtrados;
    if (categoriaActual === 'todos') {
        filtrados = objetivos;
    } else {
        filtrados = objetivos.filter(obj => (obj.categoria || 'diario') === categoriaActual);
    }
    if (filtrados.length === 0) {
        lista.innerHTML = '<li class="list-group-item text-center text-muted">No hay objetivos para esta categoría.</li>';
        actualizarResumenObjetivos();
        return;
    }
    filtrados.forEach((obj, idx) => {
        // Formateo de fechas en español
        const fechaCreacion = obj.fecha_creacion ? new Date(obj.fecha_creacion + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
        const fechaInicio = obj.fecha_inicio ? new Date(obj.fecha_inicio + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
        const fechaFin = obj.fecha_fin ? new Date(obj.fecha_fin + 'T12:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }) : '';
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex align-items-center';
        if (obj.completado) li.classList.add('objetivo-completado');
        li.innerHTML = `
            <div style="flex:1;min-width:0;">
                <input type="checkbox" class="form-check-input me-2 check-objetivo" ${obj.completado ? 'checked' : ''} data-id="${obj.id}">
                <span class="objetivo-titulo">${obj.titulo}</span>
                <span class="etiqueta-prioridad ${obj.prioridad}">${obj.prioridad.charAt(0).toUpperCase() + obj.prioridad.slice(1)}</span>
                ${obj.categoria ? `<span class="etiqueta-categoria">${obj.categoria.charAt(0).toUpperCase() + obj.categoria.slice(1)}</span>` : ''}
                ${obj.estado ? `<span class="badge bg-secondary ms-1">${obj.estado.replace('_', ' ').toUpperCase()}</span>` : ''}
                ${obj.descripcion ? `<div class="objetivo-desc">${obj.descripcion}</div>` : ''}
                <div class="objetivo-extra mt-1 small text-muted">
                    ${fechaCreacion ? `<span class="objetivo-fecha"><i class='bi bi-calendar-plus'></i> Creado: ${fechaCreacion}</span>` : ''}
                    ${obj.recompensa ? `<span class="objetivo-recompensa"><i class='bi bi-gift'></i> ${obj.recompensa}</span>` : ''}
                    ${fechaInicio ? `<span class="objetivo-fecha"><i class='bi bi-calendar-event'></i> Inicio: ${fechaInicio}</span>` : ''}
                    ${fechaFin ? `<span class="objetivo-fecha"><i class='bi bi-calendar-check'></i> Fin: ${fechaFin}</span>` : ''}
                    ${obj.horas_estimadas ? `<span class="objetivo-horas"><i class='bi bi-clock'></i> ${obj.horas_estimadas}h</span>` : ''}
                    ${obj.dificultad ? `<span class="objetivo-dificultad"><i class='bi bi-bar-chart'></i> Dificultad: ${obj.dificultad}</span>` : ''}
                    ${obj.etiquetas ? `<span class="objetivo-etiquetas"><i class='bi bi-tags'></i> ${obj.etiquetas}</span>` : ''}
                </div>
                ${obj.notas_adicionales ? `<div class="objetivo-notas small text-info mt-1"><i class='bi bi-info-circle'></i> ${obj.notas_adicionales}</div>` : ''}
            </div>
            <div class="acciones-objetivo">
                <button class="btn-editar" title="Editar" data-id="${obj.id}"><i class="bi bi-pencil"></i></button>
                <button class="btn-eliminar" title="Eliminar" data-id="${obj.id}"><i class="bi bi-trash"></i></button>
            </div>
        `;
        lista.appendChild(li);
    });
    actualizarResumenObjetivos();
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
    const horasEstimadas = document.getElementById('modal-horas-estimadas-objetivo').value || null;
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
      if (result.status === 'success') {
        await cargarObjetivos();
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalNuevoObjetivo'));
        if (modal) modal.hide();
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
    const horasEstimadas = document.getElementById('editar-horas-estimadas-objetivo').value || null;
    const dificultad = document.getElementById('editar-dificultad-objetivo').value || null;
    const etiquetas = document.getElementById('editar-etiquetas-objetivo').value.trim();
    const recompensa = document.getElementById('editar-recompensa-objetivo').value.trim();
    const notasAdicionales = document.getElementById('editar-notas-adicionales-objetivo').value.trim();
    const chkRecEdit = document.getElementById('editar-recurrente-objetivo');
    let recurrente = chkRecEdit.checked;
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
        await cargarObjetivos();
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditarObjetivo'));
        if (modal) modal.hide();
      } else {
        showError(result.error || 'Error al actualizar objetivo');
      }
    } catch (err) {
      showError('Error al actualizar objetivo');
    }
  });
}

// Render inicial desde API
cargarObjetivos();

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
        // Setear el valor actual si existe
        setTimeout(() => {
            const select = document.getElementById('editar-padre-objetivo');
            if (select && window.objetivoEditandoPadreId) {
                select.value = window.objetivoEditandoPadreId;
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
    const btn = e.target.closest('.btn-editar');
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
    document.getElementById('editar-horas-estimadas-objetivo').value = objetivo.horas_estimadas || '';
    document.getElementById('editar-dificultad-objetivo').value = objetivo.dificultad || '';
    document.getElementById('editar-etiquetas-objetivo').value = objetivo.etiquetas || '';
    document.getElementById('editar-recompensa-objetivo').value = objetivo.recompensa || '';
    document.getElementById('editar-notas-adicionales-objetivo').value = objetivo.notas_adicionales || '';
    document.getElementById('editar-recurrente-objetivo').checked = !!objetivo.recurrente;
    // Mostrar el modal
    const modal = new bootstrap.Modal(document.getElementById('modalEditarObjetivo'));
    modal.show();
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
    document.getElementById('modal-dificultad-objetivo').value = '';
    document.getElementById('modal-etiquetas-objetivo').value = '';
    document.getElementById('modal-recompensa-objetivo').value = '';
    document.getElementById('modal-notas-adicionales-objetivo').value = '';
    document.getElementById('modal-recurrente-objetivo').checked = false;
}

document.addEventListener('click', async function(e) {
    const btnEliminar = e.target.closest('.btn-eliminar');
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
