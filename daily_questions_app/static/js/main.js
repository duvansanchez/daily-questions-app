console.log('JS CARGADO');

// Variables globales
let currentQuestionIndex = 0;
let questions = [];
let responses = {};
let questionTimers = {}; // Para almacenar los timers de cada pregunta
let questionStartTimes = {}; // Para almacenar los tiempos de inicio
let mapaObjetivosPadre = {};
let categoriaActual = 'diario';

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
let ordenActual = 'orden'; // Variable global para el ordenamiento

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
            separador.className = 'separador-objetivos';
            separador.innerHTML = '<hr class="my-3"><div class="text-center text-muted fw-semibold mb-2">Objetivos Completados</div>';
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
        const card = document.createElement('div');
        card.className = 'objetivo-card mb-3';
        if (obj.completado) card.classList.add('objetivo-completado');
        if (obj.saltado_hoy) card.classList.add('objetivo-inactivo-hoy');
        if (!obj.completado && !obj.saltado_hoy && obj.estado !== 'histórico') card.classList.add('resaltado-activo');
        card.innerHTML = `
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
        lista.appendChild(card);
        // Cargar y renderizar subobjetivos para este objetivo
        cargarYRenderizarSubobjetivos(obj.id);
    });
    // Evento para el botón Saltar hoy
    document.querySelectorAll('.btn-saltar-hoy').forEach(btn => {
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
    document.querySelectorAll('.btn-reactivar-hoy').forEach(btn => {
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
                await agregarSubobjetivo(objetivoId, titulo); // Usa la función global reforzada
                input.value = '';
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

window.cargarYRenderizarSubobjetivos = cargarYRenderizarSubobjetivos;

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
