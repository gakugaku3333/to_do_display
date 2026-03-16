'use strict';

const REFRESH_INTERVAL_MS = 60 * 1000;

// ===== 時計 =====
function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  document.getElementById('clock').textContent = `${h}:${m}`;
}

setInterval(updateClock, 1000);
updateClock();

// ===== 日付表示 =====
function updateDateDisplay(data) {
  const dateEl = document.getElementById('date-info');
  const d = new Date(data.date + 'T00:00:00');
  const year = d.getFullYear();
  const month = d.getMonth() + 1;
  const day = d.getDate();
  dateEl.innerHTML = `${year}年${month}月${day}日<br>${data.weekday}`;
}

// ===== イベント描画 =====
function renderEvents(events) {
  const list = document.getElementById('events-list');
  list.innerHTML = '';

  if (events.length === 0) {
    list.innerHTML = '<div class="empty-state">今日の予定はありません</div>';
    return;
  }

  for (const ev of events) {
    const el = document.createElement('div');
    el.className = 'event-item';

    const dot = document.createElement('div');
    dot.className = 'event-dot';
    dot.style.background = ev.color;

    const timeEl = document.createElement('div');
    timeEl.className = 'event-time';
    if (ev.is_all_day) {
      timeEl.textContent = '';
    } else {
      timeEl.textContent = ev.start_time;
    }

    const titleEl = document.createElement('div');
    titleEl.className = 'event-title';
    titleEl.textContent = ev.title;

    el.appendChild(dot);
    el.appendChild(timeEl);
    el.appendChild(titleEl);

    if (ev.is_all_day) {
      const badge = document.createElement('div');
      badge.className = 'event-allday';
      badge.textContent = '終日';
      el.appendChild(badge);
    }

    list.appendChild(el);
  }
}

// ===== タスク描画 =====
function formatDueDate(dueDateStr, isOverdue) {
  if (!dueDateStr) return '';
  const d = new Date(dueDateStr + 'T00:00:00');
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const label = isOverdue ? `⚠ 期限切れ: ${m}/${day}` : `期限: ${m}/${day}`;
  return label;
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

function renderTasks(tasks, listId) {
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

// ===== タップ処理 =====
async function handleTaskTap(el, task) {
  const isCompleted = el.classList.contains('completed');
  const endpoint = isCompleted
    ? `/api/tasks/${task.id}/uncomplete`
    : `/api/tasks/${task.id}/complete`;

  // 楽観的 UI 更新
  if (isCompleted) {
    el.classList.remove('completed');
  } else {
    el.classList.add('completed');
  }

  try {
    const body = isCompleted
      ? null
      : JSON.stringify({ task_type: task.task_type, due_date: task.due_date || null });

    await fetch(endpoint, {
      method: 'POST',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body,
    });
  } catch (e) {
    // 失敗したらロールバック
    if (isCompleted) {
      el.classList.add('completed');
    } else {
      el.classList.remove('completed');
    }
    console.error('タスク更新エラー:', e);
  }
}

// ===== データ取得と描画 =====
async function fetchAndRender() {
  const indicator = document.getElementById('refresh-indicator');
  indicator.classList.remove('hidden');

  try {
    const res = await fetch('/api/today');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    updateDateDisplay(data);
    renderEvents(data.events);
    renderTasks(data.stock_tasks, 'stock-list');
    renderTasks(data.flow_tasks, 'flow-list');

    document.getElementById('flow-title').textContent =
      `🔄 ${data.weekday}のタスク`;
  } catch (e) {
    console.error('データ取得エラー:', e);
  } finally {
    indicator.classList.add('hidden');
  }
}

// ===== イベントデリゲーション (innerHTML 上書き後もリスナーが生きる) =====
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

// ===== Screen Wake Lock (タブレットのスリープ防止) =====
async function requestWakeLock() {
  try {
    await navigator.wakeLock.request('screen');
  } catch (_) { /* 非対応ブラウザでは無視 */ }
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') requestWakeLock();
});

requestWakeLock();

// ===== 初期化 =====
fetchAndRender();
setInterval(fetchAndRender, REFRESH_INTERVAL_MS);
