// 一時的な接続状態バナー（SSE切断/再接続など）。常時警告を出す health-banner とは別枠。

export function showStatusBanner(message, type) {
  const el = document.getElementById('status-banner');
  el.textContent = message;
  el.className = `status-banner ${type}`;
}

export function hideStatusBanner() {
  const el = document.getElementById('status-banner');
  el.className = 'hidden';
}

export function flashStatus(message, type, ms = 3000) {
  showStatusBanner(message, type);
  setTimeout(hideStatusBanner, ms);
}
