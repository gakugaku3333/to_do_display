import { postProposalAction } from '../api.js';
import { flashStatus } from './statusBanner.js';
import { getState, setState } from '../state.js';
import { dismissOnBackdrop } from '../utils.js';

const CHILD_COLORS = {
  '紗奈': '#9b59b6',
  '和花': '#27ae60',
  '舞':   '#e67e22',
};

let currentIndex = 0;

function openModal() {
  const proposals = getState().proposals;
  if (proposals.length === 0) return;
  currentIndex = 0;
  renderCard();
  document.getElementById('proposals-overlay').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('proposals-overlay').classList.add('hidden');
}

function renderCard() {
  const proposals = getState().proposals;
  const proposal = proposals[currentIndex];
  const counter = document.getElementById('proposals-counter');
  counter.textContent = `${currentIndex + 1} / ${proposals.length}`;

  const card = document.getElementById('proposals-card');
  const color = CHILD_COLORS[proposal.child_name] || '#888';
  const dateStr = proposal.event_date.replace(/-/g, '/');
  const timeStr = proposal.time_start
    ? (proposal.time_end ? `${proposal.time_start}〜${proposal.time_end}` : proposal.time_start)
    : '終日';

  card.innerHTML = `
    <div class="proposal-child-badge" style="background:${color}">${proposal.child_name}</div>
    <div class="proposal-event-title">${proposal.title}</div>
    <div class="proposal-meta">
      <span class="proposal-date">📅 ${dateStr}</span>
      <span class="proposal-time">🕐 ${timeStr}</span>
    </div>
    ${proposal.location ? `<div class="proposal-location">📍 ${proposal.location}</div>` : ''}
    ${proposal.description ? `<div class="proposal-desc">${proposal.description}</div>` : ''}
    ${proposal.image_filename ? `<div class="proposal-source">配布物: ${proposal.image_filename}</div>` : ''}
  `;
}

async function handleAction(action) {
  const proposals = getState().proposals;
  const proposal = proposals[currentIndex];

  try {
    await postProposalAction(proposal.id, action);
  } catch (e) {
    flashStatus('処理に失敗しました', 'error');
    return;
  }

  const remaining = proposals.filter((p) => p.id !== proposal.id);
  setState({ proposals: remaining });

  if (remaining.length === 0) {
    closeModal();
  } else {
    if (currentIndex >= remaining.length) currentIndex = remaining.length - 1;
    renderCard();
  }
}

// render(state): #proposals-badge のみを触る（モーダル内容はアクション時に個別更新）。
export function render(state) {
  const badge = document.getElementById('proposals-badge');
  const count = state.proposals.length;
  if (count > 0) {
    badge.textContent = `📄 ${count}`;
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

export function initProposals() {
  document.getElementById('btn-approve').addEventListener('click', () => handleAction('approve'));
  document.getElementById('btn-reject').addEventListener('click', () => handleAction('reject'));
  document.getElementById('proposals-badge').addEventListener('click', openModal);
  dismissOnBackdrop('proposals-overlay', closeModal);
}
