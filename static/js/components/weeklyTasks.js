import { fetchWeeklyTasks, createWeeklyTask, updateWeeklyTask, deleteWeeklyTask } from '../api.js';
import { flashStatus } from './statusBanner.js';
import { escapeHtml, WEEKDAY_LABELS, jsDayToJa, dismissOnBackdrop } from '../utils.js';

function buildDaySelector(containerId, selectedDays = []) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';
  const todayJa = jsDayToJa(new Date().getDay());
  WEEKDAY_LABELS.forEach((label, i) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'day-toggle' + (selectedDays.includes(i) ? ' selected' : '') + (i === todayJa ? ' today-mark' : '');
    btn.textContent = label;
    btn.dataset.day = i;
    btn.addEventListener('click', () => btn.classList.toggle('selected'));
    container.appendChild(btn);
  });
}

function getSelectedDays(containerId) {
  return [...document.querySelectorAll(`#${containerId} .day-toggle.selected`)]
    .map((b) => parseInt(b.dataset.day));
}

function renderDayChips(weekdays) {
  const todayJa = jsDayToJa(new Date().getDay());
  return WEEKDAY_LABELS.map((label, i) => {
    if (!weekdays.includes(i)) return '';
    const cls = i === todayJa ? 'day-chip today' : 'day-chip active';
    return `<span class="${cls}">${label}</span>`;
  }).join('');
}

async function refreshList() {
  const tasks = await fetchWeeklyTasks();
  renderTaskList(tasks);
}

function renderTaskList(tasks) {
  const list = document.getElementById('weekly-task-list');
  list.innerHTML = '';

  if (tasks.length === 0) {
    list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-secondary);font-size:0.9rem">まだ曜日タスクがありません</div>';
    return;
  }

  tasks.forEach((task) => {
    const row = document.createElement('div');
    row.className = 'weekly-task-row';
    row.dataset.taskId = task.id;

    const display = document.createElement('div');
    display.className = 'weekly-task-display';
    const trashBadge = task.category === 'trash' ? '<span class="trash-badge">🗑️ ゴミ出し</span>' : '';
    display.innerHTML = `
      <span class="weekly-task-title">${escapeHtml(task.title)}${trashBadge}</span>
      <div class="weekly-task-days">${renderDayChips(task.weekdays)}</div>
      <div class="weekly-task-actions">
        <button class="weekly-btn edit-btn">✏</button>
        <button class="weekly-btn delete delete-btn">🗑</button>
      </div>`;

    const editForm = document.createElement('div');
    editForm.className = 'weekly-task-edit';
    editForm.style.display = 'none';
    const editSelectorId = `edit-days-${task.id}`;
    const editTrashId = `edit-trash-${task.id}`;
    editForm.innerHTML = `
      <input type="text" class="edit-title-input" value="${escapeHtml(task.title)}" maxlength="50">
      <div id="${editSelectorId}" class="day-selector"></div>
      <label class="weekly-edit-trash-label">
        <input type="checkbox" id="${editTrashId}" ${task.category === 'trash' ? 'checked' : ''}>
        🗑️ ゴミ出し
      </label>
      <div class="weekly-edit-actions">
        <button class="weekly-cancel-btn">キャンセル</button>
        <button class="weekly-save-btn">保存</button>
      </div>`;

    row.appendChild(display);
    row.appendChild(editForm);
    list.appendChild(row);

    display.querySelector('.edit-btn').addEventListener('click', () => {
      display.style.display = 'none';
      editForm.style.display = 'flex';
      editForm.style.flexDirection = 'column';
      buildDaySelector(editSelectorId, task.weekdays);
      editForm.querySelector('.edit-title-input').focus();
    });

    editForm.querySelector('.weekly-cancel-btn').addEventListener('click', () => {
      editForm.style.display = 'none';
      display.style.display = 'flex';
    });

    editForm.querySelector('.weekly-save-btn').addEventListener('click', async () => {
      const title = editForm.querySelector('.edit-title-input').value.trim();
      const days = getSelectedDays(editSelectorId);
      if (!title || days.length === 0) return;
      const category = document.getElementById(editTrashId).checked ? 'trash' : 'task';
      const res = await updateWeeklyTask(task.id, title, days, category);
      if (res.ok) await refreshList();
    });

    display.querySelector('.delete-btn').addEventListener('click', async () => {
      if (!confirm(`「${task.title}」を削除しますか？`)) return;
      const res = await deleteWeeklyTask(task.id);
      if (res.ok) await refreshList();
    });
  });
}

async function openModal() {
  document.getElementById('weekly-overlay').classList.remove('hidden');
  buildDaySelector('weekly-add-days');
  document.getElementById('weekly-add-title').value = '';
  document.getElementById('weekly-add-btn').disabled = true;
  await refreshList();
}

function closeModal() {
  document.getElementById('weekly-overlay').classList.add('hidden');
}

export function initWeeklyTasks() {
  document.getElementById('weekly-settings-btn').addEventListener('click', openModal);
  document.getElementById('weekly-close-btn').addEventListener('click', closeModal);
  dismissOnBackdrop('weekly-overlay', closeModal);

  const addTitleInput = document.getElementById('weekly-add-title');
  const addBtn = document.getElementById('weekly-add-btn');

  addTitleInput.addEventListener('input', () => {
    addBtn.disabled = !addTitleInput.value.trim();
  });

  addBtn.addEventListener('click', async () => {
    const title = addTitleInput.value.trim();
    const days = getSelectedDays('weekly-add-days');
    if (!title || days.length === 0) {
      flashStatus('タスク名と曜日を入力してください', 'warning', 2000);
      return;
    }
    const trashCheckbox = document.getElementById('weekly-add-trash');
    const category = trashCheckbox.checked ? 'trash' : 'task';
    const res = await createWeeklyTask(title, days, category);
    if (res.ok) {
      addTitleInput.value = '';
      addBtn.disabled = true;
      trashCheckbox.checked = false;
      buildDaySelector('weekly-add-days');
      await refreshList();
    }
  });
}
