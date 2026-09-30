/**
 * Apex Productivity Dashboard • Frontend Logic
 * Full Monthly Calendar Grid (Left) + Task & Deadline Sidebar (Right)
 */

let allTasks = [];
let allRoutines = [];
let allNotes = [];
let diaryDates = [];
let currentFilter = 'all';
let currentRoutineFilter = 'all';
let currentView = 'today';
let calendarMode = 'bs'; // 'bs' or 'ad'
let selectedCalendarDate = null;
let selectedDiaryDate = new Date().toISOString().slice(0, 10);
let showingDiaryHistory = false;

let currentBsYear = 2083;
let currentBsMonth = 5;
let currentAdYear = 2026;
let currentAdMonth = 9;

// DOM Elements
const adDateEl = document.getElementById('ad-date');
const adSubEl = document.getElementById('ad-sub');
const liveClockEl = document.getElementById('live-clock');
const bsDateEl = document.getElementById('bs-date');
const bsNpDateEl = document.getElementById('bs-np-date');
const bsRituEl = document.getElementById('bs-ritu');

const calMonthHeading = document.getElementById('cal-month-heading');
const calSpanSub = document.getElementById('cal-span-sub');
const monthDaysGrid = document.getElementById('month-days-grid');
const btnPrevMonth = document.getElementById('btn-prev-month');
const btnTodayMonth = document.getElementById('btn-today-month');
const btnNextMonth = document.getElementById('btn-next-month');
const btnToggleBs = document.getElementById('btn-toggle-bs');
const btnToggleAd = document.getElementById('btn-toggle-ad');

// Today Focus Elements
const btnToday = document.getElementById('btn-show-today');
const todaySection = document.getElementById('today-section');
const todayRoutinesContainer = document.getElementById('today-routines-container');
const todayTasksContainer = document.getElementById('today-tasks-container');
const countTodayEl = document.getElementById('count-today');
const countTodayRoutinesEl = document.getElementById('count-today-routines');
const countTodayTasksEl = document.getElementById('count-today-tasks');
const todayRoutinesPill = document.getElementById('today-routines-pill');
const todayTasksPill = document.getElementById('today-tasks-pill');
const todayTitleEl = document.getElementById('today-title');
const todaySubtitleEl = document.getElementById('today-subtitle');
const btnGotoRoutines = document.getElementById('btn-goto-routines');
const btnGotoTasks = document.getElementById('btn-goto-tasks');

// Tasks Filter Banner
const taskDateFilterBanner = document.getElementById('task-date-filter-banner');
const taskDateFilterText = document.getElementById('task-date-filter-text');
const btnClearTaskFilter = document.getElementById('btn-clear-task-filter');
const btnAddTaskFiltered = document.getElementById('btn-add-task-filtered');
const tasksFilterGroup = document.getElementById('tasks-filter-group');

const tasksContainer = document.getElementById('tasks-container');
const routinesContainer = document.getElementById('routines-container');
const notesContainer = document.getElementById('notes-container');
const quickForm = document.getElementById('quick-add-form');
const quickInput = document.getElementById('quick-input');
const autocompleteEl = document.getElementById('autocomplete-suggestions');

const countAllEl = document.getElementById('count-all');
const countActiveEl = document.getElementById('count-active');
const countUrgentEl = document.getElementById('count-urgent');
const countDoneEl = document.getElementById('count-done');
const countRoutinesEl = document.getElementById('count-routines');
const countNotesEl = document.getElementById('count-notes');

const countRoutineAllEl = document.getElementById('count-routine-all');
const countRoutineUrgentEl = document.getElementById('count-routine-urgent');
const countRoutineDoneEl = document.getElementById('count-routine-done');

// Modal Elements
const taskModal = document.getElementById('task-modal');
const modalTaskTitle = document.getElementById('modal-task-title');
const modalTaskStart = document.getElementById('modal-task-start');
const modalTaskEnd = document.getElementById('modal-task-end');
const modalTaskPriority = document.getElementById('modal-task-priority');
const modalTaskCategory = document.getElementById('modal-task-category');

// Diary Elements
const diaryDayTitle = document.getElementById('diary-day-title');
const diaryBsSubtitle = document.getElementById('diary-bs-subtitle');
const diaryHistoryPanel = document.getElementById('diary-history-panel');

document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  fetchInitialData();
  requestNotificationPermission();
  
  setInterval(tickClock, 1000);
  setInterval(updateLiveCountdowns, 1000);
  setInterval(updateRoutineCountdowns, 1000);
  setInterval(() => {
    fetchTasks(false);
    fetchRoutines(false);
    fetchNotes(false);
  }, 5000);
});

function setupEventListeners() {
  // Task Filter tabs
  document.querySelectorAll('.filter-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderTasks();
    });
  });

  // Routine Sub-Filter tabs
  document.querySelectorAll('.routine-filter-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.routine-filter-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentRoutineFilter = btn.dataset.routineFilter;
      renderRoutines();
    });
  });

  // Mode toggles (Today vs Tasks vs Routines vs Notes)
  const btnTasks = document.getElementById('btn-show-tasks');
  const btnRoutines = document.getElementById('btn-show-routines');
  const btnNotes = document.getElementById('btn-show-notes');
  const tasksSection = document.getElementById('tasks-section');
  const routinesSection = document.getElementById('routines-section');
  const notesSection = document.getElementById('notes-section');
  const filterGroup = document.getElementById('tasks-filter-group') || document.querySelector('.filter-group');

  function setView(mode) {
    currentView = mode;
    if (btnToday) btnToday.classList.toggle('active', mode === 'today');
    if (btnTasks) btnTasks.classList.toggle('active', mode === 'tasks');
    if (btnRoutines) btnRoutines.classList.toggle('active', mode === 'routines');
    if (btnNotes) btnNotes.classList.toggle('active', mode === 'notes');

    if (todaySection) todaySection.classList.toggle('active', mode === 'today');
    if (tasksSection) tasksSection.classList.toggle('active', mode === 'tasks');
    if (routinesSection) routinesSection.classList.toggle('active', mode === 'routines');
    if (notesSection) notesSection.classList.toggle('active', mode === 'notes');

    if (filterGroup) {
      filterGroup.style.opacity = mode === 'tasks' ? '1' : '0.4';
      filterGroup.style.pointerEvents = mode === 'tasks' ? 'auto' : 'none';
    }
  }

  if (btnToday) {
    btnToday.addEventListener('click', () => {
      setView('today');
      renderTodayView();
    });
  }

  if (btnTasks) {
    btnTasks.addEventListener('click', () => {
      setView('tasks');
      renderTasks();
    });
  }

  if (btnRoutines) {
    btnRoutines.addEventListener('click', () => {
      setView('routines');
      renderRoutines();
    });
  }

  if (btnNotes) {
    btnNotes.addEventListener('click', () => {
      setView('notes');
      renderNotes();
    });
  }

  if (btnGotoRoutines) {
    btnGotoRoutines.addEventListener('click', () => {
      setView('routines');
      renderRoutines();
    });
  }

  if (btnGotoTasks) {
    btnGotoTasks.addEventListener('click', () => {
      setView('tasks');
      renderTasks();
    });
  }

  if (btnClearTaskFilter) {
    btnClearTaskFilter.addEventListener('click', () => {
      clearCalendarFilter();
    });
  }

  if (btnAddTaskFiltered) {
    btnAddTaskFiltered.addEventListener('click', () => {
      openTaskModal(selectedCalendarDate);
    });
  }

  // Task creation modal triggers
  const btnOpenModal = document.getElementById('btn-open-task-modal');
  const btnCloseModal = document.getElementById('btn-close-task-modal');
  const btnCancelModal = document.getElementById('btn-cancel-task-modal');
  const btnSaveModal = document.getElementById('btn-save-task-modal');

  if (btnOpenModal) btnOpenModal.addEventListener('click', () => openTaskModal());
  if (btnCloseModal) btnCloseModal.addEventListener('click', () => closeTaskModal());
  if (btnCancelModal) btnCancelModal.addEventListener('click', () => closeTaskModal());
  if (btnSaveModal) btnSaveModal.addEventListener('click', () => saveTaskModal());
  if (modalTaskTitle) {
    modalTaskTitle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') saveTaskModal();
    });
  }

  // Routine quick add
  const routineSubmitBtn = document.getElementById('routine-submit-btn');
  const routineTitleInput = document.getElementById('routine-title-input');
  const routineCatInput = document.getElementById('routine-cat-input');
  const btnTestWebNotify = document.getElementById('btn-test-web-notify');

  if (routineSubmitBtn) routineSubmitBtn.addEventListener('click', () => submitRoutine());
  if (routineTitleInput) routineTitleInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') submitRoutine(); });
  if (routineCatInput) routineCatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') submitRoutine(); });
  if (btnTestWebNotify) btnTestWebNotify.addEventListener('click', () => testWebNotification());

  // Diary navigation triggers
  const btnDiaryPrev = document.getElementById('btn-diary-prev');
  const btnDiaryToday = document.getElementById('btn-diary-today');
  const btnDiaryNext = document.getElementById('btn-diary-next');
  const btnDiaryHistory = document.getElementById('btn-diary-history');

  if (btnDiaryPrev) btnDiaryPrev.addEventListener('click', () => changeDiaryDay(-1));
  if (btnDiaryToday) btnDiaryToday.addEventListener('click', () => {
    selectedDiaryDate = new Date().toISOString().slice(0, 10);
    fetchNotes();
  });
  if (btnDiaryNext) btnDiaryNext.addEventListener('click', () => changeDiaryDay(1));
  if (btnDiaryHistory) btnDiaryHistory.addEventListener('click', () => toggleDiaryHistory());

  // Calendar Navigation
  btnPrevMonth.addEventListener('click', () => {
    if (calendarMode === 'bs') {
      if (currentBsMonth === 1) { currentBsMonth = 12; currentBsYear--; }
      else { currentBsMonth--; }
    } else {
      if (currentAdMonth === 1) { currentAdMonth = 12; currentAdYear--; }
      else { currentAdMonth--; }
    }
    renderMonthCalendar();
  });

  btnNextMonth.addEventListener('click', () => {
    if (calendarMode === 'bs') {
      if (currentBsMonth === 12) { currentBsMonth = 1; currentBsYear++; }
      else { currentBsMonth++; }
    } else {
      if (currentAdMonth === 12) { currentAdMonth = 1; currentAdYear++; }
      else { currentAdMonth++; }
    }
    renderMonthCalendar();
  });

  btnTodayMonth.addEventListener('click', () => {
    fetchInitialData();
  });

  btnToggleBs.addEventListener('click', () => {
    calendarMode = 'bs';
    btnToggleBs.classList.add('active');
    btnToggleAd.classList.remove('active');
    renderMonthCalendar();
  });

  btnToggleAd.addEventListener('click', () => {
    calendarMode = 'ad';
    btnToggleAd.classList.add('active');
    btnToggleBs.classList.remove('active');
    renderMonthCalendar();
  });

  // Quick add form & Autocomplete
  quickForm.addEventListener('submit', handleQuickAdd);
  quickInput.addEventListener('input', handleAutocomplete);

  // Note form
  const noteSubmitBtn = document.getElementById('note-submit-btn');
  const noteInput = document.getElementById('note-input');
  noteSubmitBtn.addEventListener('click', () => submitNote());
  noteInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitNote();
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== quickInput && document.activeElement !== noteInput && document.activeElement !== modalTaskTitle) {
      e.preventDefault();
      quickInput.focus();
    }
    if (e.key === 'Escape' && !taskModal.classList.contains('hidden')) {
      closeTaskModal();
    }
  });
}

async function fetchInitialData() {
  await fetchCalendarHeader();
  await fetchDiaryDates();
  await fetchTasks();
  await fetchRoutines();
  await fetchNotes();
  await renderMonthCalendar();
}

async function fetchDiaryDates() {
  try {
    const res = await fetch('/api/diary/dates');
    if (!res.ok) return;
    diaryDates = await res.json();
  } catch (err) {
    console.error('Error fetching diary dates:', err);
  }
}

// 1. Dual Calendar Header
async function fetchCalendarHeader() {
  try {
    const res = await fetch('/api/calendar');
    if (!res.ok) return;
    const data = await res.json();
    
    adDateEl.textContent = data.ad.formatted;
    adSubEl.textContent = `${data.ad.weekday}, Week of year`;

    bsDateEl.textContent = `${data.bs.formatted_en} BS`;
    bsNpDateEl.textContent = `${data.bs.formatted_np} (${data.bs.weekday_name_np})`;
    bsRituEl.textContent = `${data.bs.ritu_en} (${data.bs.ritu_np})`;

    currentBsYear = data.bs.year;
    currentBsMonth = data.bs.month;
    currentAdYear = data.ad.year;
    currentAdMonth = data.ad.month;
  } catch (err) {
    console.error('Error fetching calendar header:', err);
  }
}

function tickClock() {
  const now = new Date();
  liveClockEl.textContent = now.toLocaleTimeString('en-US', { hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// 2. Full Monthly Calendar Grid
async function renderMonthCalendar() {
  try {
    const endpoint = (calendarMode === 'bs') 
      ? `/api/calendar/month/bs?year=${currentBsYear}&month=${currentBsMonth}`
      : `/api/calendar/month/ad?year=${currentAdYear}&month=${currentAdMonth}`;
      
    const res = await fetch(endpoint);
    if (!res.ok) return;
    const data = await res.json();

    if (calendarMode === 'bs') {
      calMonthHeading.textContent = `${data.month_name_en} ${data.year_bs} BS (${data.month_name_np} ${data.year_np})`;
      calSpanSub.textContent = `• ${data.ad_span}`;
    } else {
      calMonthHeading.textContent = `${data.month_name} ${data.year_ad} AD`;
      calSpanSub.textContent = `• ${data.bs_span}`;
    }

    const cells = data.cells || [];
    let gridHtml = '';

    for (let i = 0; i < 42; i++) {
      if (i < cells.length && cells[i] !== null) {
        const c = cells[i];
        const isToday = c.is_today ? 'today' : '';
        const isSat = c.is_saturday ? 'saturday' : '';
        const adIso = c.ad_date_iso;

        let primaryNum = (calendarMode === 'bs') ? c.bs_day : c.ad_day;
        let dualNum = (calendarMode === 'bs') ? `${c.ad_month} ${c.ad_day}` : `${(c.bs_month_name || '').slice(0, 3)} ${c.bs_day}`;

        // Check for matching active uncompleted tasks on this date
        const matchingTasks = allTasks.filter(t => !t.is_completed && t.start_date.slice(0, 10) <= adIso && adIso <= t.end_date.slice(0, 10));
        let pillsHtml = '';
        if (matchingTasks.length > 0) {
          const firstTask = matchingTasks[0];
          const isUrgent = matchingTasks.some(t => t.priority === 'urgent' || t.priority === 'high');
          const pillText = matchingTasks.length === 1 ? firstTask.title : `${matchingTasks.length} tasks`;
          pillsHtml = `<div class="cell-task-pill ${isUrgent ? 'urgent' : ''}" title="${escapeHtml(firstTask.title)}">${escapeHtml(pillText)}</div>`;
        }

        // Check for completed tasks on this date (completed on this day)
        const completedOnDate = allTasks.filter(t => t.is_completed && t.completed_at && t.completed_at.slice(0, 10) === adIso);
        let donePillHtml = '';
        if (completedOnDate.length > 0) {
          donePillHtml = `<div class="cell-done-pill" title="Completed on this day: ${completedOnDate.map(t => escapeHtml(t.title)).join(', ')}">✓ ${completedOnDate.length} done</div>`;
        }

        // Check for diary entries on this date
        const hasDiary = diaryDates.some(d => d.date === adIso);
        const diaryHtml = hasDiary ? `<div class="cell-diary-indicator">📔 Diary</div>` : '';
        const isSelected = (selectedCalendarDate === adIso || (currentView === 'notes' && selectedDiaryDate === adIso)) ? 'selected' : '';

        gridHtml += `
          <div class="cal-cell ${isToday} ${isSat} ${isSelected}" onclick="selectCalendarDate('${adIso}')">
            <div class="cell-num-row">
              <span class="cell-primary-num">${primaryNum}</span>
              <span class="cell-dual-num">${dualNum}</span>
            </div>
            <div class="cell-task-pills">
              ${pillsHtml}
              ${donePillHtml}
              ${diaryHtml}
            </div>
          </div>
        `;
      } else {
        gridHtml += `<div class="cal-cell empty"></div>`;
      }
    }

    monthDaysGrid.innerHTML = gridHtml;
  } catch (err) {
    console.error('Error rendering calendar grid:', err);
  }
}

// Modal & Calendar Select Functions
function openTaskModal(dateIso) {
  const defaultDate = dateIso || new Date().toISOString().slice(0, 10);
  if (modalTaskTitle) modalTaskTitle.value = '';
  if (modalTaskStart) modalTaskStart.value = defaultDate;
  if (modalTaskEnd) modalTaskEnd.value = defaultDate;
  if (modalTaskPriority) modalTaskPriority.value = 'normal';
  if (modalTaskCategory) modalTaskCategory.value = 'work';
  if (taskModal) taskModal.classList.remove('hidden');
  if (modalTaskTitle) modalTaskTitle.focus();
}

function closeTaskModal() {
  if (taskModal) taskModal.classList.add('hidden');
}

async function saveTaskModal() {
  const title = modalTaskTitle ? modalTaskTitle.value.trim() : '';
  if (!title) return;
  const startDate = (modalTaskStart && modalTaskStart.value) || new Date().toISOString().slice(0, 10);
  const endDate = (modalTaskEnd && modalTaskEnd.value) || startDate;
  const priority = (modalTaskPriority && modalTaskPriority.value) || 'normal';
  const category = (modalTaskCategory && modalTaskCategory.value.trim()) || 'general';

  try {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        start_date: startDate,
        end_date: endDate,
        priority,
        category
      })
    });
    if (res.ok) {
      closeTaskModal();
      await fetchTasks();
      renderMonthCalendar();
    }
  } catch (err) {
    console.error('Error saving task:', err);
  }
}

function selectCalendarDate(dateIso) {
  if (selectedCalendarDate === dateIso) {
    selectedCalendarDate = null;
  } else {
    selectedCalendarDate = dateIso;
    selectedDiaryDate = dateIso;
  }

  renderMonthCalendar();

  if (currentView === 'notes') {
    fetchNotes();
  } else {
    const btnTasks = document.getElementById('btn-show-tasks');
    if (btnTasks && currentView !== 'tasks') {
      btnTasks.click();
    } else {
      renderTasks();
    }
  }
}

function clearCalendarFilter() {
  selectedCalendarDate = null;
  if (taskDateFilterBanner) taskDateFilterBanner.classList.add('hidden');
  renderMonthCalendar();
  renderTasks();
}

// Autocomplete Suggestions
function handleAutocomplete() {
  const text = quickInput.value;
  if (!text.trim()) {
    autocompleteEl.classList.add('hidden');
    autocompleteEl.innerHTML = '';
    return;
  }

  const todayIso = new Date().toISOString().slice(0, 10);
  const lower = text.toLowerCase();
  let suggestions = [];

  if (text.startsWith('/')) {
    if (text === '/') {
      suggestions = [
        { text: '/routine 08:30 Morning routine #routine', label: '⏰ Add Routine' },
        { text: '/note Reflection for today...', label: '📔 Add Diary Entry' }
      ];
    } else if (text.startsWith('/r')) {
      suggestions = [
        { text: text.trim().length <= 8 ? '/routine 08:30 ' : text + ' #routine', label: '⏰ Daily Routine' },
        { text: '/routine 18:00 Evening review #routine', label: '⏰ Evening Routine' }
      ];
    } else if (text.startsWith('/n')) {
      suggestions = [
        { text: text.trim().length <= 5 ? '/note ' : text, label: '📔 Diary Note' }
      ];
    }
  } else if (lower.startsWith('rou') || lower.startsWith('daily')) {
    suggestions = [
      { text: '/routine 08:30 Morning routine #routine', label: '⏰ Add Routine' },
      { text: '/routine 18:00 Evening review #routine', label: '⏰ Add Routine' }
    ];
  } else if (lower.startsWith('not') || lower.startsWith('dia')) {
    suggestions = [
      { text: `/note ${text}`, label: '📔 Add to Diary' },
      { text: '/note Reflection for today...', label: '📔 Add Diary Entry' }
    ];
  } else if (lower.startsWith('urg')) {
    suggestions = [
      { text: `${text} #urgent`, label: 'Mark #urgent' }
    ];
  } else if (text.includes('#')) {
    const lastWord = text.split(/\s+/).pop();
    if (lastWord.startsWith('#')) {
      const base = text.slice(0, text.lastIndexOf('#'));
      const tags = ['#urgent', '#high', '#normal', '#health', '#work', '#study'];
      suggestions = tags
        .filter(t => t.startsWith(lastWord))
        .map(t => ({ text: base + t, label: `Tag ${t}` }));
    }
  } else if (text.includes('@')) {
    const lastWord = text.split(/\s+/).pop();
    if (lastWord.startsWith('@')) {
      const base = text.slice(0, text.lastIndexOf('@'));
      const cats = ['@work', '@personal', '@health', '@study', '@routine'];
      suggestions = cats
        .filter(c => c.startsWith(lastWord))
        .map(c => ({ text: base + c, label: `Category ${c}` }));
    }
  } else if (lower.includes('from ') && !lower.includes('to ')) {
    suggestions = [
      { text: `${text} to ${todayIso}`, label: 'Set end date' }
    ];
  } else if (lower.includes('by ')) {
    suggestions = [
      { text: `${text} #urgent`, label: 'Mark #urgent' },
      { text: `${text} @work`, label: 'Category @work' }
    ];
  } else {
    suggestions = [
      { text: `${text} #urgent`, label: 'Priority #urgent' },
      { text: `${text} by ${todayIso}`, label: 'Due today' },
      { text: `${text} @work`, label: 'Category @work' }
    ];
  }

  if (suggestions.length === 0) {
    autocompleteEl.classList.add('hidden');
    autocompleteEl.innerHTML = '';
    return;
  }

  autocompleteEl.innerHTML = suggestions.slice(0, 4).map(s => `
    <div class="autocomplete-chip" onclick="applySuggestion('${escapeHtml(s.text)}')">
      <span class="autocomplete-text">${escapeHtml(s.text.length > 28 ? s.text.slice(0, 28) + '...' : s.text)}</span>
      <span class="autocomplete-hint">${escapeHtml(s.label)}</span>
    </div>
  `).join('');
  autocompleteEl.classList.remove('hidden');
}

function applySuggestion(val) {
  quickInput.value = val;
  quickInput.focus();
  autocompleteEl.classList.add('hidden');
  autocompleteEl.innerHTML = '';
}

// 3. Tasks Management
async function fetchTasks(showSpinner = true) {
  try {
    const res = await fetch('/api/tasks');
    if (!res.ok) return;
    allTasks = await res.json();
    updateCounts();
    renderTasks();
  } catch (err) {
    console.error('Error fetching tasks:', err);
  }
}

function isTaskCompletedToday(task, todayIso) {
  if (!task.is_completed) return false;
  const completedAt = task.completed_at || '';
  return completedAt.slice(0, 10) === todayIso;
}

function updateCounts() {
  const todayIso = new Date().toISOString().slice(0, 10);
  // Rule: In "All", uncompleted tasks + tasks completed TODAY.
  // Tasks completed yesterday or earlier are archived into Done / History.
  const allVisible = allTasks.filter(t => !t.is_completed || isTaskCompletedToday(t, todayIso));
  const active = allTasks.filter(t => !t.is_completed && !t.is_upcoming).length;
  const urgent = allTasks.filter(t => !t.is_completed && (t.is_urgent || t.priority === 'urgent' || t.priority === 'high' || t.urgency === 'critical' || t.urgency === 'warning' || t.urgency === 'overdue')).length;
  const done = allTasks.filter(t => t.is_completed).length;

  countAllEl.textContent = allVisible.length;
  countActiveEl.textContent = active;
  countUrgentEl.textContent = urgent;
  countDoneEl.textContent = done;

  renderTodayView();
}

// Today View Renderer
function renderTodayView() {
  if (!todaySection) return;
  const now = new Date();
  const todayIso = now.toISOString().slice(0, 10);

  if (todayTitleEl) {
    todayTitleEl.textContent = `⭐ Today's Remaining Focus`;
  }
  if (todaySubtitleEl) {
    todaySubtitleEl.textContent = `${todayIso} • Uncompleted routines & remaining tasks`;
  }

  // 1. Remaining Routines for Today (what I haven't done routine)
  const remainingRoutines = allRoutines.filter(r => !r.is_completed_today);
  if (countTodayRoutinesEl) countTodayRoutinesEl.textContent = remainingRoutines.length;
  if (todayRoutinesPill) todayRoutinesPill.textContent = `${remainingRoutines.length} routines left`;

  if (todayRoutinesContainer) {
    if (remainingRoutines.length === 0) {
      const msg = allRoutines.length > 0
        ? '✓ All routines completed for today! Great job! 🎉'
        : 'No routines scheduled today. Add one in Routines tab!';
      todayRoutinesContainer.innerHTML = `
        <div class="empty-state" style="padding: 10px 8px; border: 1px dashed rgba(16,185,129,0.3); border-radius: 8px;">
          <p style="color:var(--accent-emerald); font-size:11.5px; font-weight:700;">${msg}</p>
        </div>
      `;
    } else {
      todayRoutinesContainer.innerHTML = remainingRoutines.map(r => {
        const isDue = r.is_due_now ? 'urgency-critical' : '';
        const bellIcon = r.notify ? '🔔' : '🔕';
        const bellClass = r.notify ? '' : 'muted';

        return `
          <div class="task-card ${isDue}" id="today-routine-card-${r.id}">
            <div class="task-check-wrapper" onclick="toggleRoutineTodayFromTodayView(${r.id})">
              <div class="custom-checkbox">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </div>
            </div>

            <div class="task-details">
              <div class="task-title-row">
                <span class="range-pill" style="color:var(--accent-sky);">[${r.time_12h || r.time_str}]</span>
                <span class="task-title" title="${escapeHtml(r.title)}">${escapeHtml(r.title)}</span>
              </div>
              <div class="task-sub-row">
                <span class="category-tag">@${r.category || 'routine'}</span>
                <span id="today-routine-countdown-${r.id}">${r.countdown_text || ''}</span>
              </div>
            </div>

            <div class="task-badge-wrapper">
              <span class="urgency-badge ${r.badge_class || 'badge-healthy'}" id="today-routine-badge-${r.id}">
                ${r.badge_text || r.time_12h}
              </span>
            </div>

            <button class="routine-bell-btn ${bellClass}" onclick="toggleRoutineNotify(${r.id})" title="Toggle Alert">
              ${bellIcon}
            </button>
          </div>
        `;
      }).join('');
    }
  }

  // 2. Remaining Tasks for Today:
  // - Rollover / Overdue tasks from yesterday or earlier days (uncompleted)
  // - Tasks active/due today (uncompleted)
  const remainingTasks = allTasks.filter(t => {
    if (t.is_completed) return false;
    const ends = t.end_date.slice(0, 10);
    const starts = t.start_date.slice(0, 10);
    const isPastDue = (ends < todayIso) || (t.seconds_remaining < 0);
    const isActiveToday = (starts <= todayIso && todayIso <= ends);
    return isPastDue || isActiveToday;
  });

  // Sort: Overdue/rollover from past first, then due today
  remainingTasks.sort((a, b) => {
    const aEnds = a.end_date.slice(0, 10);
    const bEnds = b.end_date.slice(0, 10);
    if (aEnds < todayIso && bEnds >= todayIso) return -1;
    if (bEnds < todayIso && aEnds >= todayIso) return 1;
    return (a.seconds_remaining || 0) - (b.seconds_remaining || 0);
  });

  if (countTodayTasksEl) countTodayTasksEl.textContent = remainingTasks.length;
  if (todayTasksPill) todayTasksPill.textContent = `${remainingTasks.length} tasks remaining`;

  const totalTodayRemaining = remainingRoutines.length + remainingTasks.length;
  if (countTodayEl) countTodayEl.textContent = totalTodayRemaining;

  if (todayTasksContainer) {
    if (remainingTasks.length === 0) {
      todayTasksContainer.innerHTML = `
        <div class="empty-state" style="padding: 10px 8px; border: 1px dashed rgba(16,185,129,0.3); border-radius: 8px;">
          <p style="color:var(--accent-emerald); font-size:11.5px; font-weight:700;">✓ All tasks completed for today! 🎉</p>
        </div>
      `;
    } else {
      todayTasksContainer.innerHTML = remainingTasks.map(t => {
        const isOverdue = (t.end_date.slice(0, 10) < todayIso) || (t.seconds_remaining < 0);
        let rolloverBadge = '';
        if (isOverdue) {
          const ends = new Date(t.end_date.slice(0, 10) + 'T00:00:00');
          const todayDt = new Date(todayIso + 'T00:00:00');
          const diffDays = Math.max(1, Math.round((todayDt - ends) / 86400000));
          if (diffDays === 1 || t.is_from_yesterday) {
            rolloverBadge = `<span class="rollover-pill" title="Incomplete from yesterday">⚠️ From yesterday (-1d)</span>`;
          } else {
            rolloverBadge = `<span class="rollover-pill" title="Incomplete from ${diffDays} days ago">⚠️ Remaining -${diffDays}d</span>`;
          }
        }

        const rangeTagHtml = t.range_tag 
          ? `<span class="range-pill">[${t.range_tag}]</span>` 
          : '';

        return `
          <div class="task-card ${t.urgency_class || (isOverdue ? 'urgency-overdue' : '')}" id="today-task-card-${t.id}">
            <div class="task-check-wrapper" onclick="toggleTaskFromTodayView(${t.id})">
              <div class="custom-checkbox">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </div>
            </div>

            <div class="task-details">
              <div class="task-title-row">
                <span class="task-title" title="${escapeHtml(t.title)}">${escapeHtml(t.title)}</span>
                ${rolloverBadge}
                ${rangeTagHtml}
              </div>
              <div class="task-sub-row">
                <span class="category-tag">@${t.category || 'general'}</span>
                <span id="today-task-countdown-${t.id}">${t.countdown_text || ''}</span>
              </div>
            </div>

            <div class="task-badge-wrapper">
              <span class="urgency-badge ${t.badge_class || (isOverdue ? 'badge-overdue pulse-red' : 'badge-healthy')}" id="today-task-badge-${t.id}">
                ${t.badge_text || (isOverdue ? '-1d overdue' : 'Due Today')}
              </span>
            </div>

            <button class="btn-delete-task" onclick="deleteTask(${t.id})" title="Delete Task">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        `;
      }).join('');
    }
  }
}

async function toggleRoutineTodayFromTodayView(routineId) {
  await toggleRoutineToday(routineId);
  renderTodayView();
}

async function toggleTaskFromTodayView(taskId) {
  await toggleTask(taskId);
  renderTodayView();
}

function renderTasks() {
  const todayIso = new Date().toISOString().slice(0, 10);
  let filtered = [];

  if (selectedCalendarDate) {
    if (taskDateFilterBanner) {
      taskDateFilterBanner.classList.remove('hidden');
      if (taskDateFilterText) taskDateFilterText.textContent = `Filtered Date: ${selectedCalendarDate}`;
    }

    const dayTasks = allTasks.filter(t => {
      const starts = t.start_date.slice(0, 10);
      const ends = t.end_date.slice(0, 10);
      const completedOn = t.completed_at ? t.completed_at.slice(0, 10) : '';
      return (starts <= selectedCalendarDate && selectedCalendarDate <= ends) || completedOn === selectedCalendarDate || ends === selectedCalendarDate;
    });

    if (currentFilter === 'active') {
      filtered = dayTasks.filter(t => !t.is_completed);
    } else if (currentFilter === 'urgent') {
      filtered = dayTasks.filter(t => !t.is_completed && (t.is_urgent || t.priority === 'urgent' || t.priority === 'high' || t.urgency === 'critical' || t.urgency === 'warning' || t.urgency === 'overdue'));
    } else if (currentFilter === 'completed') {
      filtered = dayTasks.filter(t => t.is_completed);
    } else {
      // "all" on this day: show all tasks for this day (both active and completed on this day)
      filtered = dayTasks;
    }
  } else {
    if (taskDateFilterBanner) taskDateFilterBanner.classList.add('hidden');

    if (currentFilter === 'active') {
      filtered = allTasks.filter(t => !t.is_completed && !t.is_upcoming);
    } else if (currentFilter === 'urgent') {
      filtered = allTasks.filter(t => !t.is_completed && (t.is_urgent || t.priority === 'urgent' || t.priority === 'high' || t.urgency === 'critical' || t.urgency === 'warning' || t.urgency === 'overdue'));
    } else if (currentFilter === 'completed') {
      // Done tab: shows all completed tasks in history
      filtered = allTasks.filter(t => t.is_completed);
    } else {
      // "all" filter:
      // USER REQUIREMENT:
      // - Show all uncompleted tasks (including tasks not completed yesterday/past with minus day overdue tag)
      // - If completed today: show that task!
      // - If completed yesterday or earlier: DO NOT SHOW in "all", it belongs to history / Done tab!
      filtered = allTasks.filter(t => !t.is_completed || isTaskCompletedToday(t, todayIso));
    }
  }

  if (filtered.length === 0) {
    let emptyMsg = 'No tasks found in this view.';
    if (selectedCalendarDate) {
      emptyMsg = `No tasks recorded on ${selectedCalendarDate}.<br><button class="cal-btn-sm" style="margin-top:6px;" onclick="openTaskModal('${selectedCalendarDate}')">+ Add Task for this day</button>`;
    } else if (currentFilter === 'completed') {
      emptyMsg = 'No completed tasks yet in history.<br>Check off a task to move it here!';
    }
    tasksContainer.innerHTML = `
      <div class="empty-state">
        <p>${emptyMsg}</p>
        ${!selectedCalendarDate ? '<p style="font-size:11px; margin-top:4px; color:var(--text-dim);">Type below to add one!</p>' : ''}
      </div>
    `;
    return;
  }

  tasksContainer.innerHTML = filtered.map(t => createTaskCardHtml(t)).join('');
}

function createTaskCardHtml(task) {
  const todayIso = new Date().toISOString().slice(0, 10);
  const isChecked = task.is_completed ? 'checked' : '';
  const titleClass = task.is_completed ? 'completed' : '';
  const rangeTagHtml = task.range_tag 
    ? `<span class="range-pill" title="Origin (Start): ${task.start_date} | Deadline: ${task.end_date}">[${task.range_tag}]</span>` 
    : '';

  // Rollover / overdue tag
  let rolloverHtml = '';
  if (!task.is_completed) {
    const ends = task.end_date.slice(0, 10);
    if (ends < todayIso || task.seconds_remaining < 0) {
      const endsDt = new Date(ends + 'T00:00:00');
      const todayDt = new Date(todayIso + 'T00:00:00');
      const diffDays = Math.max(1, Math.round((todayDt - endsDt) / 86400000));
      if (diffDays === 1 || task.is_from_yesterday) {
        rolloverHtml = `<span class="rollover-pill" title="Remaining from yesterday">⚠️ From yesterday (-1d)</span>`;
      } else {
        rolloverHtml = `<span class="rollover-pill" title="Remaining from minus ${diffDays} days">⚠️ Remaining -${diffDays}d</span>`;
      }
    }
  } else {
    // If completed, show when
    if (isTaskCompletedToday(task, todayIso)) {
      rolloverHtml = `<span class="history-pill" style="color:var(--accent-emerald); font-size:9.5px; font-weight:700; background:rgba(16,185,129,0.15); padding:1px 5px; border-radius:4px;">✓ Done today</span>`;
    } else {
      const doneDate = (task.completed_at || '').slice(0, 10);
      rolloverHtml = `<span class="history-pill" style="color:var(--text-dim); font-size:9px; background:rgba(255,255,255,0.06); padding:1px 5px; border-radius:4px;">Done: ${doneDate}</span>`;
    }
  }

  return `
    <div class="task-card ${task.urgency_class}" id="task-card-${task.id}">
      <div class="task-check-wrapper" onclick="toggleTask(${task.id})">
        <div class="custom-checkbox ${isChecked}">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
      </div>

      <div class="task-details">
        <div class="task-title-row">
          <span class="task-title ${titleClass}" title="${escapeHtml(task.title)}">${escapeHtml(task.title)}</span>
          ${rolloverHtml}
          ${rangeTagHtml}
        </div>
        <div class="task-sub-row">
          <span class="category-tag">@${task.category || 'general'}</span>
          <span id="task-countdown-${task.id}">${task.countdown_text}</span>
        </div>
      </div>

      <div class="task-badge-wrapper">
        <span class="urgency-badge ${task.badge_class}" id="task-badge-${task.id}">
          ${task.badge_text}
        </span>
      </div>

      <button class="btn-delete-task" onclick="deleteTask(${task.id})" title="Delete Task">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
        </svg>
      </button>
    </div>
  `;
}

// 4. Live Countdown Updater
function updateLiveCountdowns() {
  const now = new Date();

  allTasks.forEach(task => {
    if (task.is_completed) return;

    const startDt = new Date(task.start_date.replace(' ', 'T'));
    const endDt = new Date(task.end_date.replace(' ', 'T'));
    const isUpcoming = (now < startDt);
    const totalSec = Math.floor((endDt - now) / 1000);
    const priority = (task.priority || 'normal').toLowerCase();
    const isUrgentPriority = (priority === 'urgent' || priority === 'critical');
    const isHighPriority = (priority === 'high');

    const badgeEl = document.getElementById(`task-badge-${task.id}`);
    const countdownEl = document.getElementById(`task-countdown-${task.id}`);
    const cardEl = document.getElementById(`task-card-${task.id}`);
    if (!badgeEl || !countdownEl) return;

    let badgeText = '';
    let countdownText = '';
    let badgeClass = '';
    let urgencyClass = '';

    if (totalSec < 0) {
      const absSec = Math.abs(totalSec);
      const days = Math.floor(absSec / 86400);
      const hours = Math.floor((absSec % 86400) / 3600);
      badgeText = days > 0 ? `-${days}d overdue` : `-${hours}h overdue`;
      countdownText = `Overdue by ${days > 0 ? days + 'd ' : ''}${hours}h`;
      badgeClass = 'urgency-badge badge-overdue pulse-red';
      urgencyClass = 'urgency-overdue';
    } else if (isUpcoming) {
      const startSec = Math.floor((startDt - now) / 1000);
      const startDays = Math.floor(startSec / 86400);
      const startHours = Math.floor((startSec % 86400) / 3600);
      if (startDays > 1) {
        countdownText = `Starts in ${startDays} days`;
        badgeText = isUrgentPriority ? `Urgent • In ${startDays}d` : (isHighPriority ? `High • In ${startDays}d` : `In ${startDays} days`);
      } else if (startDays === 1) {
        countdownText = `Starts tomorrow (${startHours}h)`;
        badgeText = isUrgentPriority ? 'Urgent • 1d' : 'Starts tomorrow';
      } else if (startHours > 0) {
        countdownText = `Starts in ${startHours}h`;
        badgeText = `In ${startHours}h`;
      } else {
        countdownText = 'Starts soon';
        badgeText = 'Starting soon';
      }
      if (isUrgentPriority) {
        badgeClass = 'urgency-badge badge-critical pulse-red';
        urgencyClass = 'urgency-critical';
      } else if (isHighPriority) {
        badgeClass = 'urgency-badge badge-warning';
        urgencyClass = 'urgency-warning';
      } else {
        badgeClass = 'urgency-badge badge-upcoming';
        urgencyClass = 'urgency-upcoming';
      }
    } else if (totalSec < 86400) {
      const hours = Math.floor(totalSec / 3600);
      const mins = Math.floor((totalSec % 3600) / 60);
      const secs = totalSec % 60;
      badgeText = hours > 0 ? `${hours}h left!` : `${mins}m ${secs}s!`;
      countdownText = `${hours}h ${mins}m left`;
      badgeClass = 'urgency-badge badge-critical pulse-red';
      urgencyClass = 'urgency-critical';
    } else if (isUrgentPriority) {
      const days = Math.floor(totalSec / 86400);
      badgeText = days > 1 ? `Urgent • ${days}d left` : `Urgent • 1d left`;
      countdownText = `${days} days remaining`;
      badgeClass = 'urgency-badge badge-critical pulse-red';
      urgencyClass = 'urgency-critical';
    } else if (totalSec <= 3 * 86400 || isHighPriority) {
      const days = Math.floor(totalSec / 86400);
      const hours = Math.floor((totalSec % 86400) / 3600);
      badgeText = isHighPriority ? `High • ${days}d left` : (days > 1 ? `${days} days left` : `1d ${hours}h left`);
      countdownText = `${days}d ${hours}h remaining`;
      badgeClass = 'urgency-badge badge-warning';
      urgencyClass = 'urgency-warning';
    } else {
      const days = Math.floor(totalSec / 86400);
      badgeText = `${days} days left`;
      countdownText = `${days} days remaining`;
      badgeClass = 'urgency-badge badge-healthy';
      urgencyClass = 'urgency-healthy';
    }

    if (badgeEl) {
      badgeEl.textContent = badgeText;
      badgeEl.className = badgeClass;
    }
    if (countdownEl) countdownEl.textContent = countdownText;
    if (cardEl) cardEl.className = `task-card ${urgencyClass}`;

    const todayBadgeEl = document.getElementById(`today-task-badge-${task.id}`);
    const todayCountdownEl = document.getElementById(`today-task-countdown-${task.id}`);
    const todayCardEl = document.getElementById(`today-task-card-${task.id}`);
    if (todayBadgeEl) {
      todayBadgeEl.textContent = badgeText;
      todayBadgeEl.className = badgeClass;
    }
    if (todayCountdownEl) todayCountdownEl.textContent = countdownText;
    if (todayCardEl) todayCardEl.className = `task-card ${urgencyClass}`;
  });
}

// 5. Quick Add Command Handler
async function handleQuickAdd(e) {
  e.preventDefault();
  const text = quickInput.value.trim();
  if (!text) return;

  try {
    const res = await fetch('/api/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: text })
    });

    if (res.ok) {
      const result = await res.json();
      quickInput.value = '';
      if (autocompleteEl) {
        autocompleteEl.classList.add('hidden');
        autocompleteEl.innerHTML = '';
      }
      if (result.type === 'note') {
        await fetchDiaryDates();
        await fetchNotes();
        renderMonthCalendar();
        document.getElementById('btn-show-notes').click();
      } else if (result.type === 'routine') {
        await fetchRoutines();
        document.getElementById('btn-show-routines').click();
      } else {
        await fetchTasks();
        renderMonthCalendar();
      }
    }
  } catch (err) {
    console.error('Error submitting quick add:', err);
  }
}

async function toggleTask(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/toggle`, { method: 'PUT' });
    if (res.ok) {
      await fetchTasks();
      renderMonthCalendar();
    }
  } catch (err) {
    console.error('Error toggling task:', err);
  }
}

async function deleteTask(taskId) {
  try {
    const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    if (res.ok) {
      await fetchTasks();
      renderMonthCalendar();
    }
  } catch (err) {
    console.error('Error deleting task:', err);
  }
}

// 6. Day-Specific Daily Diary (Notes)
async function fetchNotes(showSpinner = true) {
  try {
    const res = await fetch(`/api/notes?date=${selectedDiaryDate}`);
    if (!res.ok) return;
    allNotes = await res.json();
    countNotesEl.textContent = allNotes.length;
    updateDiaryHeader();
    renderNotes();
  } catch (err) {
    console.error('Error fetching notes:', err);
  }
}

function updateDiaryHeader() {
  try {
    const d = new Date(selectedDiaryDate + 'T00:00:00');
    const isToday = (selectedDiaryDate === new Date().toISOString().slice(0, 10));
    diaryDayTitle.textContent = `📔 ${d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })}${isToday ? ' (Today)' : ''}`;
    diaryBsSubtitle.textContent = `Selected Date: ${selectedDiaryDate} • Daily reflections & memory log`;
  } catch (e) {
    diaryDayTitle.textContent = `📔 Date: ${selectedDiaryDate}`;
  }
}

function changeDiaryDay(delta) {
  try {
    const d = new Date(selectedDiaryDate + 'T00:00:00');
    d.setDate(d.getDate() + delta);
    selectedDiaryDate = d.toISOString().slice(0, 10);
    fetchNotes();
  } catch (e) {}
}

async function toggleDiaryHistory() {
  showingDiaryHistory = !showingDiaryHistory;
  if (!showingDiaryHistory) {
    diaryHistoryPanel.classList.add('hidden');
    return;
  }
  await fetchDiaryDates();
  if (diaryDates.length === 0) {
    diaryHistoryPanel.innerHTML = '<span style="font-size:10px; color:var(--text-dim); padding:4px;">No past diary entries yet.</span>';
  } else {
    diaryHistoryPanel.innerHTML = `
      <div style="font-size:10px; font-weight:700; color:var(--accent-gold); margin-bottom:4px;">Past Journal Dates:</div>
      ${diaryDates.slice(0, 10).map(d => `
        <div class="diary-history-chip" onclick="selectDiaryDate('${d.date}')">
          <span>📅 ${d.date}</span>
          <span>${d.count} ${d.count === 1 ? 'entry' : 'entries'}</span>
        </div>
      `).join('')}
    `;
  }
  diaryHistoryPanel.classList.remove('hidden');
}

function selectDiaryDate(dateIso) {
  selectedDiaryDate = dateIso;
  showingDiaryHistory = false;
  diaryHistoryPanel.classList.add('hidden');
  fetchNotes();
}

function renderNotes() {
  if (allNotes.length === 0) {
    notesContainer.innerHTML = `
      <div class="empty-state">
        <p>No diary entries for ${selectedDiaryDate}.</p>
        <p style="font-size:11px; margin-top:4px; color:var(--text-dim);">Write your thoughts and achievements above!</p>
      </div>
    `;
    return;
  }

  notesContainer.innerHTML = allNotes.map(n => {
    const timePart = (n.created_at || '').split(' ')[1] ? n.created_at.split(' ')[1].slice(0, 5) : '';
    return `
      <div class="note-card" style="border-left: 3px solid var(--accent-gold);">
        <div style="flex:1;">
          <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;">
            <span style="background:rgba(251,191,36,0.15); color:var(--accent-gold); font-size:9.5px; font-weight:700; padding:1px 5px; border-radius:4px;">🕒 ${timePart}</span>
          </div>
          <div class="note-text">${escapeHtml(n.content)}</div>
        </div>
        <button class="btn-delete-task" onclick="deleteNote(${n.id})" title="Delete Note">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `;
  }).join('');
}

async function submitNote() {
  const noteInput = document.getElementById('note-input');
  const text = noteInput.value.trim();
  if (!text) return;

  try {
    const res = await fetch('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: text, date: selectedDiaryDate })
    });
    if (res.ok) {
      noteInput.value = '';
      await fetchDiaryDates();
      await fetchNotes();
      renderMonthCalendar();
    }
  } catch (err) {
    console.error('Error adding note:', err);
  }
}

async function deleteNote(noteId) {
  try {
    const res = await fetch(`/api/notes/${noteId}`, { method: 'DELETE' });
    if (res.ok) {
      await fetchDiaryDates();
      await fetchNotes();
      renderMonthCalendar();
    }
  } catch (err) {
    console.error('Error deleting note:', err);
  }
}

function insertExample(text) {
  quickInput.value = text;
  quickInput.focus();
}

function escapeHtml(str) {
  return (str || '').replace(/[&<>"']/g, (m) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[m]);
}

// 7. Daily Routines Management with Sub-Filters
async function fetchRoutines(showSpinner = true) {
  try {
    const res = await fetch('/api/routines');
    if (!res.ok) return;
    allRoutines = await res.json();
    updateRoutineCounts();
    renderRoutines();
  } catch (err) {
    console.error('Error fetching routines:', err);
  }
}

function isUrgentRoutine(r) {
  const parts = (r.time_str || '09:00').split(':');
  const now = new Date();
  const sched = new Date(now.getFullYear(), now.getMonth(), now.getDate(), parseInt(parts[0], 10), parseInt(parts[1], 10), 0);
  const diffSec = Math.floor((sched - now) / 1000);
  return diffSec >= -300 && diffSec <= 3600;
}

function updateRoutineCounts() {
  const done = allRoutines.filter(r => r.is_completed_today).length;
  const uncompleted = allRoutines.filter(r => !r.is_completed_today);
  const total = allRoutines.length;
  const countAll = uncompleted.length;
  const countUrgent = uncompleted.filter(r => r.is_due_now || isUrgentRoutine(r)).length;
  const countDone = done;

  if (countRoutinesEl) countRoutinesEl.textContent = `${done}/${total}`;
  if (countRoutineAllEl) countRoutineAllEl.textContent = countAll;
  if (countRoutineUrgentEl) countRoutineUrgentEl.textContent = countUrgent;
  if (countRoutineDoneEl) countRoutineDoneEl.textContent = countDone;

  const routinesSub = document.getElementById('routines-sub-summary');
  if (routinesSub) {
    routinesSub.textContent = `${done} of ${total} routines completed today • Automated alerts active`;
  }
}

function renderRoutines() {
  if (!routinesContainer) return;
  updateRoutineCounts();

  let filtered = [];
  if (currentRoutineFilter === 'urgent') {
    filtered = allRoutines.filter(r => !r.is_completed_today && (r.is_due_now || isUrgentRoutine(r)));
  } else if (currentRoutineFilter === 'completed') {
    filtered = allRoutines.filter(r => r.is_completed_today);
  } else {
    // "all": ONLY uncompleted routines per user requirement
    // "if daily routine task complete then that should not show in all"
    filtered = allRoutines.filter(r => !r.is_completed_today);
  }

  if (filtered.length === 0) {
    let emptyMsg = 'No routines in this view.';
    if (currentRoutineFilter === 'completed') {
      emptyMsg = 'No routines completed yet today.<br>Check one off to see it here!';
    } else if (currentRoutineFilter === 'urgent') {
      emptyMsg = 'No urgent routines right now.<br>Everything on track!';
    } else {
      emptyMsg = allRoutines.some(r => r.is_completed_today)
        ? 'All routines completed for today! 🎉<br>Check "Done" tab to review.'
        : 'No daily routines configured.<br>Add one above to get automated reminders!';
    }
    routinesContainer.innerHTML = `
      <div class="empty-state">
        <p>${emptyMsg}</p>
      </div>
    `;
    return;
  }

  routinesContainer.innerHTML = filtered.map(r => {
    const isChecked = r.is_completed_today ? 'checked' : '';
    const titleClass = r.is_completed_today ? 'completed' : '';
    const isDue = r.is_due_now ? 'urgency-critical' : '';
    const bellIcon = r.notify ? '🔔' : '🔕';
    const bellClass = r.notify ? '' : 'muted';

    return `
      <div class="task-card ${isDue}" id="routine-card-${r.id}">
        <div class="task-check-wrapper" onclick="toggleRoutineToday(${r.id})">
          <div class="custom-checkbox ${isChecked}">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
        </div>

        <div class="task-details">
          <div class="task-title-row">
            <span class="range-pill" style="color:var(--accent-sky);">[${r.time_12h || r.time_str}]</span>
            <span class="task-title ${titleClass}" title="${escapeHtml(r.title)}">${escapeHtml(r.title)}</span>
          </div>
          <div class="task-sub-row">
            <span class="category-tag">@${r.category || 'routine'}</span>
            <span id="routine-countdown-${r.id}">${r.countdown_text || ''}</span>
          </div>
        </div>

        <div class="task-badge-wrapper">
          <span class="urgency-badge ${r.badge_class || 'badge-healthy'}" id="routine-badge-${r.id}">
            ${r.badge_text || r.time_12h}
          </span>
        </div>

        <button class="routine-bell-btn ${bellClass}" onclick="toggleRoutineNotify(${r.id})" title="Toggle Alert (On/Off)">
          ${bellIcon}
        </button>

        <button class="btn-delete-task" onclick="testRoutine(${r.id})" title="Test Alert Now">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          </svg>
        </button>

        <button class="btn-delete-task" onclick="deleteRoutine(${r.id})" title="Delete Routine">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    `;
  }).join('');
}

function updateRoutineCountdowns() {
  const now = new Date();

  allRoutines.forEach(r => {
    if (r.is_completed_today) return;

    const parts = (r.time_str || '09:00').split(':');
    const rHour = parseInt(parts[0], 10);
    const rMin = parseInt(parts[1], 10);

    const schedDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), rHour, rMin, 0);
    const diffSec = Math.floor((schedDate - now) / 1000);

    const badgeEl = document.getElementById(`routine-badge-${r.id}`);
    const cdEl = document.getElementById(`routine-countdown-${r.id}`);
    const cardEl = document.getElementById(`routine-card-${r.id}`);

    let rBadgeText = '';
    let rBadgeClass = '';
    let rCdText = '';
    let rUrgencyClass = 'task-card';

    if (diffSec >= -300 && diffSec <= 60) {
      rBadgeText = 'Due Now!';
      rBadgeClass = 'urgency-badge badge-critical pulse-red';
      rCdText = 'Scheduled for now!';
      rUrgencyClass = 'task-card urgency-critical';

      // Check if we should fire browser notification
      if (r.notify && !r.webNotifiedThisMinute && Math.abs(diffSec) <= 60) {
        r.webNotifiedThisMinute = true;
        triggerBrowserNotification(`⏰ Daily Routine: ${r.title}`, `Scheduled for ${r.time_12h || r.time_str}. Time to get started!`);
      }
    } else if (diffSec > 60) {
      const mins = Math.floor(diffSec / 60);
      const hours = Math.floor(mins / 60);
      const remMins = mins % 60;
      rCdText = hours > 0 ? `In ${hours}h ${remMins}m` : `In ${remMins}m`;

      rBadgeText = rCdText;
      rBadgeClass = mins <= 60 ? 'urgency-badge badge-warning' : 'urgency-badge badge-upcoming';
      rCdText = `Scheduled at ${r.time_12h || r.time_str}`;
      rUrgencyClass = 'task-card';
    } else {
      const absSec = Math.abs(diffSec);
      const hours = Math.floor(absSec / 3600);
      const mins = Math.floor((absSec % 3600) / 60);
      rBadgeText = `Passed (${r.time_12h || r.time_str})`;
      rBadgeClass = 'urgency-badge badge-healthy';
      rCdText = `Passed ${hours > 0 ? hours + 'h ' : ''}${mins}m ago`;
      rUrgencyClass = 'task-card';
    }

    if (badgeEl) {
      badgeEl.textContent = rBadgeText;
      badgeEl.className = rBadgeClass;
    }
    if (cdEl) cdEl.textContent = rCdText;
    if (cardEl) cardEl.className = rUrgencyClass;

    const todayBadgeEl = document.getElementById(`today-routine-badge-${r.id}`);
    const todayCdEl = document.getElementById(`today-routine-countdown-${r.id}`);
    const todayCardEl = document.getElementById(`today-routine-card-${r.id}`);
    if (todayBadgeEl) {
      todayBadgeEl.textContent = rBadgeText;
      todayBadgeEl.className = rBadgeClass;
    }
    if (todayCdEl) todayCdEl.textContent = rCdText;
    if (todayCardEl) todayCardEl.className = rUrgencyClass;
  });
}

async function submitRoutine() {
  const titleInput = document.getElementById('routine-title-input');
  const timeInput = document.getElementById('routine-time-input');
  const catInput = document.getElementById('routine-cat-input');

  const title = titleInput ? titleInput.value.trim() : '';
  const timeStr = timeInput ? timeInput.value.trim() : '09:00';
  const category = catInput ? (catInput.value.trim() || 'routine') : 'routine';

  if (!title) return;

  try {
    const res = await fetch('/api/routines', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        time_str: timeStr,
        category: category.replace(/^@/, ''),
        notify: 1
      })
    });
    if (res.ok) {
      if (titleInput) titleInput.value = '';
      if (catInput) catInput.value = '';
      await fetchRoutines();
    }
  } catch (err) {
    console.error('Error adding routine:', err);
  }
}

async function toggleRoutineToday(routineId) {
  try {
    const res = await fetch(`/api/routines/${routineId}/toggle`, { method: 'PUT' });
    if (res.ok) {
      await fetchRoutines();
    }
  } catch (err) {
    console.error('Error toggling routine:', err);
  }
}

async function toggleRoutineNotify(routineId) {
  try {
    const res = await fetch(`/api/routines/${routineId}/notify`, { method: 'PUT' });
    if (res.ok) {
      await fetchRoutines();
    }
  } catch (err) {
    console.error('Error toggling routine notify:', err);
  }
}

async function deleteRoutine(routineId) {
  try {
    const res = await fetch(`/api/routines/${routineId}`, { method: 'DELETE' });
    if (res.ok) {
      await fetchRoutines();
    }
  } catch (err) {
    console.error('Error deleting routine:', err);
  }
}

async function testRoutine(routineId) {
  try {
    playWebChime();
    const res = await fetch(`/api/routines/${routineId}/test`, { method: 'POST' });
    if (res.ok) {
      const r = allRoutines.find(x => x.id === routineId);
      const title = r ? r.title : 'Routine';
      triggerBrowserNotification(`⏰ [Test Alert] ${title}`, `Alert successful! Scheduled daily reminder.`);
    }
  } catch (err) {
    console.error('Error testing routine alert:', err);
  }
}

function testWebNotification() {
  playWebChime();
  requestNotificationPermission();
  triggerBrowserNotification('⏰ [Test Alert] Apex Dashboard', 'Desktop notifications are active and working!');
}

function playWebChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.45);
  } catch (e) {}
}

function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

function triggerBrowserNotification(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    try {
      new Notification(title, {
        body: body
      });
    } catch (e) {}
  }
}
