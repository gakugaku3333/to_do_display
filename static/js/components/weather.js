function formatTempDelta(d) {
  if (d === null || d === undefined) return '';      // 前日データなし
  if (d > 0) return `<span class="temp-delta up">(+${d}度)</span>`;
  if (d < 0) return `<span class="temp-delta down">(${d}度)</span>`;  // d は既に「−」付き
  return '<span class="temp-delta flat">(±0度)</span>';
}

// render(state): #weather-emoji / #weather-condition / #weather-temp / #weather-hourly のみを触る。
export function render(state) {
  const weather = state.data ? state.data.weather : null;

  const emojiEl     = document.getElementById('weather-emoji');
  const conditionEl = document.getElementById('weather-condition');
  const tempEl      = document.getElementById('weather-temp');
  const hourlyEl    = document.getElementById('weather-hourly');

  if (!weather) {
    emojiEl.textContent     = '—';
    conditionEl.textContent = '取得中…';
    tempEl.innerHTML        = '';
    hourlyEl.innerHTML      = '';
    return;
  }

  emojiEl.textContent     = weather.condition_emoji;
  conditionEl.textContent = weather.condition;
  // 前日比 (+N度 / -N度 / ±0度) を気温の後ろに添える
  tempEl.innerHTML =
    `↑${weather.temp_max}°${formatTempDelta(weather.temp_max_delta)} ` +
    `↓${weather.temp_min}°${formatTempDelta(weather.temp_min_delta)}`;

  hourlyEl.innerHTML = '';
  for (const h of weather.hourly_precip) {
    const p = h.precip_prob;
    const level = p >= 60 ? 'high' : p >= 30 ? 'mid' : p >= 10 ? 'low' : 'none';

    const block = document.createElement('div');
    block.className = 'precip-block';
    block.innerHTML = `
      <div class="precip-time">${h.label}</div>
      <div class="precip-pct ${level}">${p}%</div>
    `;
    hourlyEl.appendChild(block);
  }
}
