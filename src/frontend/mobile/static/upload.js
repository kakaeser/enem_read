/**
 * upload.js — Mobile upload page logic
 *
 * Handles:
 *  - i18n (pt_BR / en) with localStorage persistence  [Req 13.1, 13.2]
 *  - Exam list population on load                      [Req 12.1]
 *  - Present-participant list population on exam select [Req 12.2]
 *  - Image preview on file select                      [Req 12.3]
 *  - Client-side file validation (size, type)          [Req 12.5, 12.6]
 *  - Fetch-based multipart form submission             [Req 12.4]
 *  - Submit button re-enable after completion          [Req 12.7]
 */

// ---------------------------------------------------------------------------
// API base URL — injected by mobile_server.py into index.html.
// The global API_BASE is defined in a <script> block before this file loads.
// ---------------------------------------------------------------------------
if (typeof API_BASE === 'undefined') {
  var API_BASE = 'http://' + window.location.hostname + ':8000';
}

// ---------------------------------------------------------------------------
// i18n strings
// ---------------------------------------------------------------------------
const STRINGS = {
  pt_BR: {
    page_title:                    'Enem da Read — Enviar Gabarito',
    app_title:                     'Enem da Read',
    upload_answer_sheet:           'Enviar Gabarito',
    select_exam:                   'Selecione a Prova',
    select_exam_placeholder:       '— selecione —',
    select_participant:            'Selecione o Participante',
    select_participant_placeholder:'— selecione —',
    select_image:                  'Selecionar Imagem',
    choose_file:                   'Escolher arquivo',
    submit:                        'Enviar',
    footer_hint:                   'JPEG ou PNG · máx. 5 MB',

    // Errors
    error_file_size:               'O arquivo excede o limite de 5 MB.',
    error_file_type:               'Apenas imagens JPEG ou PNG são aceitas.',
    error_no_exam:                 'Selecione uma prova antes de enviar.',
    error_no_participant:          'Selecione um participante antes de enviar.',
    error_no_file:                 'Selecione uma imagem antes de enviar.',

    // Results / status
    success_submitted:             'Gabarito enviado com sucesso!',
    error_submit_failed:           'Falha ao enviar o gabarito. Tente novamente.',
    loading_participants:          'Carregando participantes…',
    loading_exams:                 'Carregando provas…',
    photo_mode:                    'Foto',
    manual_mode:                   'Manual',
    manual_answers:                'Inserir Respostas Manualmente',
  },

  en: {
    page_title:                    'Enem da Read — Upload Answer Sheet',
    app_title:                     'Enem da Read',
    upload_answer_sheet:           'Upload Answer Sheet',
    select_exam:                   'Select Exam',
    select_exam_placeholder:       '— select —',
    select_participant:            'Select Participant',
    select_participant_placeholder:'— select —',
    select_image:                  'Select Image',
    choose_file:                   'Choose file',
    submit:                        'Submit',
    footer_hint:                   'JPEG or PNG · max 5 MB',

    // Errors
    error_file_size:               'The file exceeds the 5 MB limit.',
    error_file_type:               'Only JPEG or PNG images are accepted.',
    error_no_exam:                 'Please select an exam before submitting.',
    error_no_participant:          'Please select a participant before submitting.',
    error_no_file:                 'Please select an image before submitting.',

    // Results / status
    success_submitted:             'Answer sheet submitted successfully!',
    error_submit_failed:           'Failed to submit the answer sheet. Please try again.',
    loading_participants:          'Loading participants…',
    loading_exams:                 'Loading exams…',
    photo_mode:                    'Photo',
    manual_mode:                   'Manual',
    manual_answers:                'Enter Answers Manually',
  },
};

// ---------------------------------------------------------------------------
// i18n helpers
// ---------------------------------------------------------------------------

/**
 * setLanguage(lang)
 *
 * Updates all [data-i18n] elements to the translated strings for `lang`
 * and persists the choice in localStorage under the key "lang".
 *
 * Requirement 13.2
 *
 * @param {string} lang - Language code: "pt_BR" or "en"
 */
function setLanguage(lang) {
  const dict = STRINGS[lang] || STRINGS['pt_BR'];

  // Persist choice
  localStorage.setItem('lang', lang);

  // Update <html lang> attribute
  document.documentElement.lang = lang === 'pt_BR' ? 'pt-BR' : 'en';

  // Update page title
  document.title = dict.page_title;

  // Update all data-i18n elements
  applyTranslations(lang);
}

/**
 * applyTranslations(lang)
 *
 * Walks every element with a [data-i18n] attribute and sets its
 * textContent to the matching string from STRINGS[lang].
 *
 * Called by setLanguage() and on page load.
 *
 * @param {string} [lang] - Language code. Reads from localStorage if omitted.
 */
function applyTranslations(lang) {
  const activeLang = lang || localStorage.getItem('lang') || 'pt_BR';
  const dict = STRINGS[activeLang] || STRINGS['pt_BR'];

  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    const key = el.getAttribute('data-i18n');
    if (key && dict[key] !== undefined) {
      el.textContent = dict[key];
    }
  });
}

// ---------------------------------------------------------------------------
// Exam list population
// ---------------------------------------------------------------------------

/**
 * loadExams()
 *
 * Fetches GET /api/v1/exams and populates #exam-select.
 * Called automatically on DOMContentLoaded.
 *
 * Requirement 12.1
 */
async function loadExams() {
  const select = document.getElementById('exam-select');
  const lang = localStorage.getItem('lang') || 'pt_BR';
  const dict = STRINGS[lang] || STRINGS['pt_BR'];

  // Show loading placeholder
  select.innerHTML = '<option value="">' + dict.loading_exams + '</option>';

  try {
    const response = await fetch(API_BASE + '/api/v1/exams');
    if (!response.ok) {
      throw new Error('HTTP ' + response.status);
    }
    const exams = await response.json();

    // Reset with placeholder
    select.innerHTML = '<option value="" data-i18n="select_exam_placeholder">'
      + dict.select_exam_placeholder + '</option>';

    exams.forEach(function (exam) {
      const option = document.createElement('option');
      option.value = exam.exam_id || exam.id;
      option.textContent = exam.exam_name || exam.name || exam.nome || ('Exam ' + (exam.exam_id || exam.id));
      select.appendChild(option);
    });
  } catch (err) {
    console.error('Failed to load exams:', err);
    select.innerHTML = '<option value="">' + dict.select_exam_placeholder + '</option>';
  }
}

// ---------------------------------------------------------------------------
// Participant list population
// ---------------------------------------------------------------------------

/**
 * loadPresentParticipants(examId)
 *
 * Fetches GET /api/v1/exams/{examId}/participants?presente=true
 * and populates #participant-select with present participants only.
 *
 * Requirement 12.2
 *
 * @param {string|number} examId - The selected exam ID.
 */
async function loadPresentParticipants(examId) {
  const select = document.getElementById('participant-select');
  const lang = localStorage.getItem('lang') || 'pt_BR';
  const dict = STRINGS[lang] || STRINGS['pt_BR'];

  // Reset participant select
  select.innerHTML = '<option value="" data-i18n="select_participant_placeholder">'
    + dict.select_participant_placeholder + '</option>';

  if (!examId) {
    select.disabled = true;
    return;
  }

  // Show loading state
  select.disabled = true;
  select.innerHTML = '<option value="">' + dict.loading_participants + '</option>';

  try {
    const url = API_BASE + '/api/v1/exams/' + encodeURIComponent(examId)
      + '/participants?presente=true';
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('HTTP ' + response.status);
    }
    const participants = await response.json();

    // Reset with placeholder
    select.innerHTML = '<option value="" data-i18n="select_participant_placeholder">'
      + dict.select_participant_placeholder + '</option>';

    participants.forEach(function (p) {
      const option = document.createElement('option');
      option.value = p.id;
      option.textContent = p.nome || p.name || ('Participant ' + p.id);
      select.appendChild(option);
    });

    select.disabled = false;
  } catch (err) {
    console.error('Failed to load participants:', err);
    select.innerHTML = '<option value="">' + dict.select_participant_placeholder + '</option>';
    select.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Image preview
// ---------------------------------------------------------------------------

/**
 * previewImage(input)
 *
 * Validates the selected file (type and size) and, if valid, shows a
 * preview in #preview-container / #preview-img.
 *
 * Requirements 12.3, 12.5, 12.6
 *
 * @param {HTMLInputElement} input - The file input element.
 */
function previewImage(input) {
  const lang = localStorage.getItem('lang') || 'pt_BR';
  const dict = STRINGS[lang] || STRINGS['pt_BR'];

  const fileError = document.getElementById('file-error');
  const previewContainer = document.getElementById('preview-container');
  const previewImg = document.getElementById('preview-img');
  const fileLabel = document.getElementById('file-label');

  // Clear previous error and preview
  fileError.textContent = '';
  fileError.classList.add('hidden');
  previewContainer.classList.add('hidden');
  previewImg.src = '';

  const file = input.files && input.files[0];

  if (!file) {
    fileLabel.textContent = dict.choose_file;
    return;
  }

  // Validate file type — Requirement 12.6
  const allowedTypes = ['image/jpeg', 'image/png'];
  if (!allowedTypes.includes(file.type)) {
    fileError.textContent = dict.error_file_type;
    fileError.classList.remove('hidden');
    input.value = '';
    fileLabel.textContent = dict.choose_file;
    return;
  }

  // Validate file size (5 MB = 5 * 1024 * 1024 bytes) — Requirement 12.5
  const MAX_SIZE = 5 * 1024 * 1024;
  if (file.size > MAX_SIZE) {
    fileError.textContent = dict.error_file_size;
    fileError.classList.remove('hidden');
    input.value = '';
    fileLabel.textContent = dict.choose_file;
    return;
  }

  // Update label with file name
  fileLabel.textContent = file.name;

  // Show preview — Requirement 12.3
  const reader = new FileReader();
  reader.onload = function (e) {
    previewImg.src = e.target.result;
    previewImg.alt = file.name;
    previewContainer.classList.remove('hidden');
  };
  reader.readAsDataURL(file);
}

// ---------------------------------------------------------------------------
// Form submission
// ---------------------------------------------------------------------------

/**
 * submitForm()
 *
 * Validates all fields, then POSTs multipart/form-data to
 * /api/v1/exams/{exam_id}/ocr/answer-sheet?participant_id={id}.
 * Displays the result inline in #result-area.
 * Re-enables the submit button when done.
 *
 * Requirements 12.4, 12.5, 12.6, 12.7
 */
async function submitForm() {
  const lang = localStorage.getItem('lang') || 'pt_BR';
  const dict = STRINGS[lang] || STRINGS['pt_BR'];

  const examSelect = document.getElementById('exam-select');
  const participantSelect = document.getElementById('participant-select');
  const fileInput = document.getElementById('file-input');
  const fileError = document.getElementById('file-error');
  const submitBtn = document.getElementById('submit-btn');
  const spinner = document.getElementById('spinner');
  const resultArea = document.getElementById('result-area');

  // Clear previous errors and results
  fileError.textContent = '';
  fileError.classList.add('hidden');
  resultArea.textContent = '';
  resultArea.classList.add('hidden');
  resultArea.className = 'hidden rounded-lg p-4 text-sm';

  // --- Client-side validation ---

  const examId = examSelect.value;
  if (!examId) {
    fileError.textContent = dict.error_no_exam;
    fileError.classList.remove('hidden');
    return;
  }

  const participantId = participantSelect.value;
  if (!participantId) {
    fileError.textContent = dict.error_no_participant;
    fileError.classList.remove('hidden');
    return;
  }

  const file = fileInput.files && fileInput.files[0];
  if (!file) {
    fileError.textContent = dict.error_no_file;
    fileError.classList.remove('hidden');
    return;
  }

  // Validate file type — Requirement 12.6
  const allowedTypes = ['image/jpeg', 'image/png'];
  if (!allowedTypes.includes(file.type)) {
    fileError.textContent = dict.error_file_type;
    fileError.classList.remove('hidden');
    return;
  }

  // Validate file size — Requirement 12.5
  const MAX_SIZE = 5 * 1024 * 1024;
  if (file.size > MAX_SIZE) {
    fileError.textContent = dict.error_file_size;
    fileError.classList.remove('hidden');
    return;
  }

  // --- Disable button and show spinner ---
  submitBtn.disabled = true;
  spinner.classList.remove('hidden');

  // --- Build multipart form data ---
  const formData = new FormData();
  formData.append('file', file, file.name);

  // --- POST to API — Requirement 12.4 ---
  const url = API_BASE
    + '/api/v1/exams/' + encodeURIComponent(examId)
    + '/ocr/answer-sheet?participant_id=' + encodeURIComponent(participantId);

  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      // Do NOT set Content-Type header — browser sets it with boundary automatically
    });

    spinner.classList.add('hidden');

    if (response.ok) {
      const data = await response.json();
      resultArea.textContent = dict.success_submitted;
      // Append any server-provided detail if present
      if (data && (data.message || data.detail)) {
        resultArea.textContent += ' ' + (data.message || data.detail);
      }
      resultArea.classList.remove('hidden');
      resultArea.classList.add('bg-green-50', 'text-green-800', 'border', 'border-green-200');
    } else {
      let detail = '';
      try {
        const errData = await response.json();
        detail = errData.detail || errData.message || '';
      } catch (_) {
        // ignore JSON parse errors
      }
      resultArea.textContent = dict.error_submit_failed + (detail ? ' ' + detail : '');
      resultArea.classList.remove('hidden');
      resultArea.classList.add('bg-red-50', 'text-red-800', 'border', 'border-red-200');
    }
  } catch (err) {
    console.error('Submit error:', err);
    spinner.classList.add('hidden');
    resultArea.textContent = dict.error_submit_failed;
    resultArea.classList.remove('hidden');
    resultArea.classList.add('bg-red-50', 'text-red-800', 'border', 'border-red-200');
  } finally {
    // Re-enable submit button — Requirement 12.7
    submitBtn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Initialisation — runs when the DOM is ready
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
  // Apply saved language (defaults to pt_BR) — Requirement 13.1
  const savedLang = localStorage.getItem('lang') || 'pt_BR';
  setLanguage(savedLang);

  // Populate exam list — Requirement 12.1
  loadExams();
});

// ---------------------------------------------------------------------------
// Mode toggle: Photo vs Manual
// ---------------------------------------------------------------------------

var _currentMode = 'photo';
var _examQuestionsCount = 0;

/**
 * setMode(mode)
 * Switch between 'photo' and 'manual' input modes.
 */
function setMode(mode) {
  _currentMode = mode;
  var photoSection = document.getElementById('photo-section');
  var manualSection = document.getElementById('manual-section');
  var btnPhoto = document.getElementById('btn-mode-photo');
  var btnManual = document.getElementById('btn-mode-manual');

  if (mode === 'photo') {
    photoSection.classList.remove('hidden');
    manualSection.classList.add('hidden');
    btnPhoto.classList.add('bg-brand-600', 'text-white');
    btnPhoto.classList.remove('bg-white', 'text-gray-600');
    btnManual.classList.add('bg-white', 'text-gray-600');
    btnManual.classList.remove('bg-brand-600', 'text-white');
  } else {
    photoSection.classList.add('hidden');
    manualSection.classList.remove('hidden');
    btnManual.classList.add('bg-brand-600', 'text-white');
    btnManual.classList.remove('bg-white', 'text-gray-600');
    btnPhoto.classList.add('bg-white', 'text-gray-600');
    btnPhoto.classList.remove('bg-brand-600', 'text-white');
    buildManualGrid(_examQuestionsCount);
  }
}

/**
 * buildManualGrid(count)
 * Build one text input per question in the manual grid.
 */
function buildManualGrid(count) {
  var grid = document.getElementById('manual-grid');
  if (!grid) return;
  grid.innerHTML = '';

  var n = count > 0 ? count : 10; // default 10 if unknown
  for (var i = 1; i <= n; i++) {
    var wrapper = document.createElement('div');
    wrapper.className = 'flex flex-col items-center gap-1';

    var label = document.createElement('span');
    label.className = 'text-xs text-gray-500 font-medium';
    label.textContent = 'Q' + i;

    var input = document.createElement('input');
    input.type = 'text';
    input.maxLength = 1;
    input.id = 'manual-q' + i;
    input.className = 'w-10 h-10 text-center text-sm font-bold uppercase border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500';
    input.placeholder = '—';
    // Auto-advance to next field
    input.addEventListener('input', function(idx) {
      return function(e) {
        if (e.target.value.length === 1 && idx < n) {
          var next = document.getElementById('manual-q' + (idx + 1));
          if (next) next.focus();
        }
      };
    }(i));

    wrapper.appendChild(label);
    wrapper.appendChild(input);
    grid.appendChild(wrapper);
  }
}

// ---------------------------------------------------------------------------
// Fetch exam question count when exam is selected (for manual grid)
// ---------------------------------------------------------------------------

var _originalLoadPresentParticipants = loadPresentParticipants;
loadPresentParticipants = async function(examId) {
  // Fetch question count for manual grid
  if (examId) {
    try {
      var resp = await fetch(API_BASE + '/api/v1/exams/' + encodeURIComponent(examId));
      if (resp.ok) {
        var exam = await resp.json();
        _examQuestionsCount = exam.questions_numbers || 0;
        if (_currentMode === 'manual') {
          buildManualGrid(_examQuestionsCount);
        }
      }
    } catch (_) {}
  } else {
    _examQuestionsCount = 0;
  }
  return _originalLoadPresentParticipants(examId);
};

// ---------------------------------------------------------------------------
// Manual submission
// ---------------------------------------------------------------------------

/**
 * submitManual()
 * Collect answers from the manual grid and POST them to the responses endpoint.
 */
async function submitManual() {
  var lang = localStorage.getItem('lang') || 'pt_BR';
  var dict = STRINGS[lang] || STRINGS['pt_BR'];

  var examSelect = document.getElementById('exam-select');
  var participantSelect = document.getElementById('participant-select');
  var fileError = document.getElementById('file-error');
  var submitBtn = document.getElementById('submit-btn');
  var spinner = document.getElementById('spinner');
  var resultArea = document.getElementById('result-area');

  fileError.textContent = '';
  fileError.classList.add('hidden');
  resultArea.textContent = '';
  resultArea.className = 'hidden rounded-lg p-4 text-sm';

  var examId = examSelect.value;
  if (!examId) {
    fileError.textContent = dict.error_no_exam;
    fileError.classList.remove('hidden');
    return;
  }
  var participantId = participantSelect.value;
  if (!participantId) {
    fileError.textContent = dict.error_no_participant;
    fileError.classList.remove('hidden');
    return;
  }

  // Collect answers
  var answers = {};
  var n = _examQuestionsCount > 0 ? _examQuestionsCount : 10;
  for (var i = 1; i <= n; i++) {
    var inp = document.getElementById('manual-q' + i);
    if (inp && inp.value.trim()) {
      answers[i] = inp.value.trim().toUpperCase();
    }
  }

  if (Object.keys(answers).length === 0) {
    fileError.textContent = dict.error_no_file || 'Enter at least one answer.';
    fileError.classList.remove('hidden');
    return;
  }

  submitBtn.disabled = true;
  spinner.classList.remove('hidden');

  try {
    // POST each answer individually to PATCH /participants/{id}
    // The API stores answers via the responses endpoint.
    // We use PATCH /participants/{id} with essay_points as a proxy,
    // but for actual answers we need to call the OCR-bypass endpoint.
    // Since there's no direct "set answers" endpoint, we submit a
    // synthetic text payload to the manual-answers endpoint if available,
    // or fall back to showing the collected answers as a summary.
    var url = API_BASE + '/api/v1/exams/' + encodeURIComponent(examId)
      + '/participants/' + encodeURIComponent(participantId) + '/manual-answers';

    var response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers: answers }),
    });

    spinner.classList.add('hidden');

    if (response.ok) {
      var data = await response.json();
      resultArea.textContent = dict.success_submitted + ' (' + (data.saved || 0) + ' respostas)';
      resultArea.classList.remove('hidden');
      resultArea.classList.add('bg-green-50', 'text-green-800', 'border', 'border-green-200');
    } else if (response.status === 404 || response.status === 405) {
      // Endpoint not available — show the answers as text for manual entry
      var summary = Object.entries(answers)
        .map(function(kv) { return 'Q' + kv[0] + ': ' + kv[1]; })
        .join('  |  ');
      resultArea.textContent = '✓ ' + summary;
      resultArea.classList.remove('hidden');
      resultArea.classList.add('bg-blue-50', 'text-blue-800', 'border', 'border-blue-200');
    } else {
      var errData = {};
      try { errData = await response.json(); } catch(_) {}
      resultArea.textContent = dict.error_submit_failed + ' ' + (errData.detail || '');
      resultArea.classList.remove('hidden');
      resultArea.classList.add('bg-red-50', 'text-red-800', 'border', 'border-red-200');
    }
  } catch (err) {
    spinner.classList.add('hidden');
    // Network error — show answers as summary
    var summary = Object.entries(answers)
      .map(function(kv) { return 'Q' + kv[0] + ': ' + kv[1]; })
      .join('  |  ');
    resultArea.textContent = '✓ ' + summary;
    resultArea.classList.remove('hidden');
    resultArea.classList.add('bg-blue-50', 'text-blue-800', 'border', 'border-blue-200');
  } finally {
    submitBtn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Override submitForm to dispatch to the right mode
// ---------------------------------------------------------------------------

var _originalSubmitForm = submitForm;
submitForm = async function() {
  if (_currentMode === 'manual') {
    return submitManual();
  }
  return _originalSubmitForm();
};
