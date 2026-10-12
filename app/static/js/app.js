/**
 * TaskFlow — app.js
 * Handles all UI interactions and communicates with the REST API.
 */

'use strict';

// ──────────────────────────────────────────────────────────────
// State
// ──────────────────────────────────────────────────────────────
let allTasks   = [];
let activeFilter = 'all';
let searchQuery  = '';

// ──────────────────────────────────────────────────────────────
// DOM references
// ──────────────────────────────────────────────────────────────
const taskList      = document.getElementById('task-list');
const emptyState    = document.getElementById('empty-state');
const loading       = document.getElementById('loading');
const addForm       = document.getElementById('add-task-form');
const titleInput    = document.getElementById('task-title');
const descInput     = document.getElementById('task-description');
const priorityInput = document.getElementById('task-priority');
const titleError    = document.getElementById('title-error');
const statTotal     = document.getElementById('stat-total');
const statCompleted = document.getElementById('stat-completed');
const statPending   = document.getElementById('stat-pending');
const searchInput   = document.getElementById('search-input');
const tabs          = document.querySelectorAll('.tab');
const statusDot     = document.getElementById('status-indicator');
const statusText    = document.getElementById('status-text');

// Edit modal
const editModal        = document.getElementById('edit-modal');
const editForm         = document.getElementById('edit-task-form');
const editTaskId       = document.getElementById('edit-task-id');
const editTitle        = document.getElementById('edit-title');
const editDescription  = document.getElementById('edit-description');
const editPriority     = document.getElementById('edit-priority');
const editTitleError   = document.getElementById('edit-title-error');
const modalCloseBtn    = document.getElementById('modal-close-btn');
const modalCancelBtn   = document.getElementById('modal-cancel-btn');

// ──────────────────────────────────────────────────────────────
// API helpers
// ──────────────────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
  };
  const response = await fetch(url, { ...defaults, ...options });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

// ──────────────────────────────────────────────────────────────
// Health check
// ──────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const data = await apiFetch('/health');
    const healthy = data.status === 'healthy';
    statusDot.className = `status-dot ${healthy ? 'green' : 'yellow'}`;
    statusText.textContent = healthy ? 'Healthy' : 'Degraded';
  } catch {
    statusDot.className = 'status-dot red';
    statusText.textContent = 'Offline';
  }
}

// ──────────────────────────────────────────────────────────────
// Fetch & render tasks
// ──────────────────────────────────────────────────────────────
async function fetchTasks() {
  showLoading(true);
  try {
    const data = await apiFetch('/api/tasks');
    allTasks = data.tasks;
    updateStats(data.stats);
    renderTasks();
  } catch (err) {
    showToast(`Failed to load tasks: ${err.message}`, 'error');
  } finally {
    showLoading(false);
  }
}

function updateStats({ total, completed, pending }) {
  statTotal.textContent     = total;
  statCompleted.textContent = completed;
  statPending.textContent   = pending;
}

function getFilteredTasks() {
  return allTasks.filter(task => {
    const matchesFilter =
      activeFilter === 'all' ||
      (activeFilter === 'completed' && task.completed) ||
      (activeFilter === 'pending'   && !task.completed);

    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      task.title.toLowerCase().includes(q) ||
      (task.description || '').toLowerCase().includes(q);

    return matchesFilter && matchesSearch;
  });
}

function renderTasks() {
  const tasks = getFilteredTasks();
  taskList.innerHTML = '';

  if (tasks.length === 0) {
    emptyState.hidden = false;
    taskList.hidden   = true;
    return;
  }
  emptyState.hidden = true;
  taskList.hidden   = false;

  tasks.forEach(task => {
    const li = createTaskElement(task);
    taskList.appendChild(li);
  });
}

function createTaskElement(task) {
  const li = document.createElement('li');
  li.className = `task-item${task.completed ? ' completed' : ''}`;
  li.dataset.id = task.id;
  li.setAttribute('role', 'listitem');

  const createdDate = task.created_at
    ? new Date(task.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : '';

  li.innerHTML = `
    <button
      class="task-checkbox"
      aria-label="${task.completed ? 'Mark as pending' : 'Mark as completed'}"
      title="${task.completed ? 'Mark as pending' : 'Mark as completed'}"
      data-action="toggle"
    >${task.completed ? '✓' : ''}</button>

    <div class="task-body">
      <div class="task-title">${escapeHtml(task.title)}</div>
      ${task.description ? `<div class="task-desc">${escapeHtml(task.description)}</div>` : ''}
      <div class="task-meta">
        <span class="priority-badge ${task.priority}">${task.priority}</span>
        ${createdDate ? `<span class="task-date">${createdDate}</span>` : ''}
      </div>
    </div>

    <div class="task-actions">
      <button class="btn-icon-only" data-action="edit"   aria-label="Edit task"   title="Edit">✏️</button>
      <button class="btn-icon-only btn-danger" data-action="delete" aria-label="Delete task" title="Delete">🗑️</button>
    </div>
  `;

  // Event delegation within the item
  li.addEventListener('click', handleTaskItemClick);
  return li;
}

function handleTaskItemClick(e) {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const taskId = parseInt(btn.closest('.task-item').dataset.id, 10);
  const action = btn.dataset.action;

  if (action === 'toggle') toggleTask(taskId);
  if (action === 'edit')   openEditModal(taskId);
  if (action === 'delete') deleteTask(taskId);
}

// ──────────────────────────────────────────────────────────────
// Add task
// ──────────────────────────────────────────────────────────────
addForm.addEventListener('submit', async e => {
  e.preventDefault();
  titleError.textContent = '';

  const title = titleInput.value.trim();
  if (!title) {
    titleError.textContent = 'Title is required.';
    titleInput.focus();
    return;
  }

  const btn = document.getElementById('add-btn');
  btn.disabled = true;
  btn.textContent = 'Adding…';

  try {
    await apiFetch('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({
        title,
        description: descInput.value.trim(),
        priority: priorityInput.value,
      }),
    });
    addForm.reset();
    showToast('Task added! ✅', 'success');
    await fetchTasks();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">＋</span> Add Task';
  }
});

// ──────────────────────────────────────────────────────────────
// Toggle completion
// ──────────────────────────────────────────────────────────────
async function toggleTask(taskId) {
  const task = allTasks.find(t => t.id === taskId);
  if (!task) return;
  try {
    await apiFetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify({ completed: !task.completed }),
    });
    showToast(task.completed ? 'Marked as pending.' : 'Task completed! 🎉', 'success');
    await fetchTasks();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

// ──────────────────────────────────────────────────────────────
// Delete task
// ──────────────────────────────────────────────────────────────
async function deleteTask(taskId) {
  if (!confirm('Delete this task? This cannot be undone.')) return;
  try {
    await apiFetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    showToast('Task deleted.', 'info');
    await fetchTasks();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

// ──────────────────────────────────────────────────────────────
// Edit modal
// ──────────────────────────────────────────────────────────────
function openEditModal(taskId) {
  const task = allTasks.find(t => t.id === taskId);
  if (!task) return;

  editTaskId.value         = task.id;
  editTitle.value          = task.title;
  editDescription.value    = task.description || '';
  editPriority.value       = task.priority;
  editTitleError.textContent = '';

  editModal.hidden = false;
  editTitle.focus();
}

function closeEditModal() {
  editModal.hidden = true;
}

modalCloseBtn.addEventListener('click',  closeEditModal);
modalCancelBtn.addEventListener('click', closeEditModal);
editModal.addEventListener('click', e => {
  if (e.target === editModal) closeEditModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !editModal.hidden) closeEditModal();
});

editForm.addEventListener('submit', async e => {
  e.preventDefault();
  editTitleError.textContent = '';

  const title = editTitle.value.trim();
  if (!title) {
    editTitleError.textContent = 'Title is required.';
    editTitle.focus();
    return;
  }

  const taskId = parseInt(editTaskId.value, 10);
  try {
    await apiFetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify({
        title,
        description: editDescription.value.trim(),
        priority: editPriority.value,
      }),
    });
    closeEditModal();
    showToast('Task updated. ✏️', 'success');
    await fetchTasks();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
});

// ──────────────────────────────────────────────────────────────
// Filter tabs
// ──────────────────────────────────────────────────────────────
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
    tab.classList.add('active');
    tab.setAttribute('aria-selected', 'true');
    activeFilter = tab.dataset.filter;
    renderTasks();
  });
});

// ──────────────────────────────────────────────────────────────
// Search
// ──────────────────────────────────────────────────────────────
searchInput.addEventListener('input', () => {
  searchQuery = searchInput.value;
  renderTasks();
});

// ──────────────────────────────────────────────────────────────
// UI helpers
// ──────────────────────────────────────────────────────────────
function showLoading(show) {
  loading.hidden = !show;
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ──────────────────────────────────────────────────────────────
// Initialise
// ──────────────────────────────────────────────────────────────
(async function init() {
  await checkHealth();
  await fetchTasks();
  // Re-check health every 30 seconds
  setInterval(checkHealth, 30_000);
})();
