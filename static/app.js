'use strict';

// ===== 認証トークン =====
const API_TOKEN = document.querySelector('meta[name="api-token"]')?.content || '';

function authHeaders(includeContentType = false) {
  const h = {};
  if (includeContentType) h['Content-Type'] = 'application/json';
  if (API_TOKEN) h['Authorization'] = `Bearer ${API_TOKEN}`;
  return h;
}

// ===== 時計 =====
function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  document.getElementById('clock').textContent = `${h}:${m}`;
}

setInterval(updateClock, 1000);
updateClock();

// ===== ステータスバナー =====
function showStatusBanner(message, type) {
  const el = document.getElementById('status-banner');
  el.textContent = message;
  el.className = `status-banner ${type}`;
}

function hideStatusBanner() {
  const el = document.getElementById('status-banner');
  el.className = 'hidden';
}

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

// ===== 統合描画 =====
function renderAll(data) {
  updateDateDisplay(data);
  renderEvents(data.events);
  renderTasks(data.stock_tasks, 'stock-list');
  renderTasks(data.flow_tasks, 'flow-list');
  document.getElementById('flow-title').textContent = `🔄 ${data.weekday}のタスク`;
}

// ===== タップ処理（重複排除付き） =====
const pendingRequests = new Map();

async function handleTaskTap(el, task) {
  // 同一タスクへの進行中リクエストをキャンセル
  if (pendingRequests.has(task.id)) {
    pendingRequests.get(task.id).abort();
  }

  const controller = new AbortController();
  pendingRequests.set(task.id, controller);

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
      headers: body ? authHeaders(true) : authHeaders(),
      body: body,
      signal: controller.signal,
    });
  } catch (e) {
    if (e.name !== 'AbortError') {
      // 失敗したらロールバック
      if (isCompleted) {
        el.classList.add('completed');
      } else {
        el.classList.remove('completed');
      }
      showStatusBanner('タスク更新に失敗しました', 'error');
      setTimeout(hideStatusBanner, 3000);
    }
  } finally {
    pendingRequests.delete(task.id);
  }
}

// ===== イベントデリゲーション =====
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

// ===== SSE接続 =====
let eventSource = null;

function connectSSE() {
  if (eventSource) {
    eventSource.close();
  }

  const url = API_TOKEN ? `/api/stream?token=${encodeURIComponent(API_TOKEN)}` : '/api/stream';
  eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      renderAll(data);
      hideStatusBanner();
    } catch (err) {
      console.error('SSEデータのパースエラー:', err);
    }
  };

  eventSource.onerror = () => {
    showStatusBanner('接続が切れました。再接続中...', 'warning');
    // EventSource は自動再接続する
  };

  eventSource.onopen = () => {
    hideStatusBanner();
  };
}

// ===== Screen Wake Lock (タブレットのスリープ防止) =====
async function requestWakeLock() {
  try {
    await navigator.wakeLock.request('screen');
  } catch (_) { /* 非対応ブラウザでは無視 */ }
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    requestWakeLock();
    // SSE接続が切れていたら再接続
    if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
      connectSSE();
    }
  }
});

requestWakeLock();

// ===== 初期化 =====
connectSSE();
