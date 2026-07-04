import { setTaskCompleted } from '../api.js';
import { flashStatus } from './statusBanner.js';

function formatDueDate(dueDateStr, isOverdue) {
  if (!dueDateStr) return '';
  const d = new Date(dueDateStr + 'T00:00:00');
  const m = d.getMonth() + 1;
  const day = d.getDate();
  return isOverdue ? `⚠ 期限切れ: ${m}/${day}` : `期限: ${m}/${day}`;
}

function createTaskElement(task) {
  const el = document.createElement('div');
  el.className = 'task-item';
  el.dataset.taskId = task.id;
  el.dataset.taskType = task.task_type;
  el.dataset.dueDate = task.due_date || '';

  if (task.is_overdue) el.classList.add('overdue');
  if (task.is_completed) el.classList.add('completed');

  const checkbox = document.createElement('div');
  checkbox.className = 'task-checkbox';
  const checkIcon = document.createElement('span');
  checkIcon.className = 'task-checkbox-icon';
  checkIcon.textContent = '✓';
  checkbox.appendChild(checkIcon);

  const content = document.createElement('div');
  content.className = 'task-content';

  const titleEl = document.createElement('div');
  titleEl.className = 'task-title';
  titleEl.textContent = task.title;
  content.appendChild(titleEl);

  if (task.due_date) {
    const dueEl = document.createElement('div');
    dueEl.className = 'task-due';
    dueEl.textContent = formatDueDate(task.due_date, task.is_overdue);
    content.appendChild(dueEl);
  }

  el.appendChild(checkbox);
  el.appendChild(content);
  return el;
}

function renderList(tasks, listId) {
  const list = document.getElementById(listId);
  list.innerHTML = '';

  if (tasks.length === 0) {
    list.innerHTML = '<div class="empty-state">タスクはありません</div>';
    return;
  }
  for (const task of tasks) {
    list.appendChild(createTaskElement(task));
  }
}

// render(state): #stock-list / #flow-list / #flow-title のみを触る。
export function render(state) {
  const data = state.data;
  if (!data) return;
  renderList(data.stock_tasks, 'stock-list');
  renderList(data.flow_tasks, 'flow-list');
  document.getElementById('flow-title').textContent = '🔄 今日のやる事リスト';
}

// ===== タップ処理（同一タスクへの連打は前のリクエストをキャンセルして重複排除） =====
const pendingRequests = new Map();

async function handleTaskTap(el, task) {
  if (pendingRequests.has(task.id)) {
    pendingRequests.get(task.id).abort();
  }
  const controller = new AbortController();
  pendingRequests.set(task.id, controller);

  const isCompleted = el.classList.contains('completed');
  // 楽観的 UI 更新
  el.classList.toggle('completed', !isCompleted);

  try {
    await setTaskCompleted(task, !isCompleted, controller.signal);
  } catch (e) {
    if (e.name !== 'AbortError') {
      el.classList.toggle('completed', isCompleted); // ロールバック
      flashStatus('タスク更新に失敗しました', 'error');
    }
  } finally {
    pendingRequests.delete(task.id);
  }
}

export function initTasks() {
  for (const listId of ['stock-list', 'flow-list']) {
    document.getElementById(listId).addEventListener('click', (e) => {
      const item = e.target.closest('.task-item');
      if (!item) return;
      const task = {
        id: item.dataset.taskId,
        task_type: item.dataset.taskType,
        due_date: item.dataset.dueDate || null,
      };
      handleTaskTap(item, task);
    });
  }
}
