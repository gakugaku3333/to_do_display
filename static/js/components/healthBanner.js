import { fetchHealth } from '../api.js';

// セルフ診断バナー (/api/health)。
// OAuthトークン失効やデータ同期停止を、家族が「予定が消えた」と気づく前に検知して常時表示する。
async function checkHealth() {
  const el = document.getElementById('health-banner');
  if (!el) return;
  try {
    const data = await fetchHealth();
    const warnings = data.warnings || [];
    if (warnings.length > 0) {
      el.textContent = '⚠ ' + warnings.join(' / ');
      el.className = '';
    } else {
      el.className = 'hidden';
    }
  } catch (err) {
    console.error('ヘルスチェックに失敗:', err);
  }
}

export function initHealthBanner() {
  checkHealth();
  setInterval(checkHealth, 10 * 60 * 1000); // 10分ごと
}
