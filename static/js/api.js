import { flashStatus } from './components/statusBanner.js';

const API_TOKEN = document.querySelector('meta[name="api-token"]')?.content || '';

export function authHeaders(includeContentType = false) {
  const h = {};
  if (includeContentType) h['Content-Type'] = 'application/json';
  if (API_TOKEN) h['Authorization'] = `Bearer ${API_TOKEN}`;
  return h;
}

export function getApiToken() {
  return API_TOKEN;
}

// fetch の共通ラッパー。ネットワーク例外やHTTPエラーを黙って握りつぶさず、
// 必ず statusBanner に到達させてから呼び出し元に再スローする（規約3）。
export async function apiFetch(url, options = {}) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    flashStatus('通信に失敗しました', 'error');
    throw err;
  }
  if (!res.ok) {
    flashStatus(`通信エラー (${res.status})`, 'error');
  }
  return res;
}

export async function fetchHealth() {
  const res = await fetch('/api/health', { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchWeeklyTasks() {
  const res = await apiFetch('/api/weekly-tasks', { headers: authHeaders() });
  return res.ok ? res.json() : [];
}

export async function createWeeklyTask(title, weekdays) {
  return apiFetch('/api/weekly-tasks', {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ title, weekdays }),
  });
}

export async function updateWeeklyTask(taskId, title, weekdays) {
  return apiFetch(`/api/weekly-tasks/${taskId}`, {
    method: 'PUT',
    headers: authHeaders(true),
    body: JSON.stringify({ title, weekdays }),
  });
}

export async function deleteWeeklyTask(taskId) {
  return apiFetch(`/api/weekly-tasks/${taskId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
}

export async function fetchWeek() {
  const res = await apiFetch('/api/week', { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function setTaskCompleted(task, completed, signal) {
  const endpoint = completed ? '/api/tasks/complete' : '/api/tasks/uncomplete';
  const body = completed
    ? JSON.stringify({ task_id: task.id, task_type: task.task_type, due_date: task.due_date || null })
    : JSON.stringify({ task_id: task.id });
  // タスク完了はユーザーが連打しても即座にキャンセルできるよう、statusBanner を経由しない
  // AbortError は握りつぶしてよいがそれ以外は呼び出し元(tasks.js)でロールバック処理に使うため
  // apiFetch を通さず直接 fetch する。
  return fetch(endpoint, { method: 'POST', headers: authHeaders(true), body, signal });
}

export async function postProposalAction(proposalId, action) {
  return apiFetch(`/api/proposals/${proposalId}/${action}`, {
    method: 'POST',
    headers: authHeaders(),
  });
}
