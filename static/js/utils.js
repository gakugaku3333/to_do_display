export function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// 日付の色分け: 祝日・日曜→holiday(赤)、土曜→saturday(青)。当日表示と週間表示で共通。
export function dateColorClass(jsDay, isHoliday) {
  if (isHoliday || jsDay === 0) return 'holiday';
  if (jsDay === 6) return 'saturday';
  return '';
}

export const WEEKDAY_LABELS = ['月', '火', '水', '木', '金', '土', '日'];

// JS: 0=日,1=月,...,6=土  /  Python(曜日タスク): 0=月,...,6=日
export function jsDayToJa(jsDay) {
  return jsDay === 0 ? 6 : jsDay - 1;
}

// オーバーレイ背景（カード外）クリックで閉じる共通ハンドラ
export function dismissOnBackdrop(overlayId, close) {
  const overlay = document.getElementById(overlayId);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });
}
