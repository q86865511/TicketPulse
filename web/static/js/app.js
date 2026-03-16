/**
 * TicketPulse — Frontend JS
 * Uses native fetch API, no external dependencies.
 */

// ── Global error handler for fetch ──────────────────────

window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled promise rejection:', e.reason);
});

// ── Utility: show toast notifications ───────────────────

function showToast(message, type = 'info') {
  const existing = document.getElementById('tp-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'tp-toast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999;
    background: ${type === 'success' ? '#57f287' : type === 'error' ? '#ed4245' : '#5865f2'};
    color: #fff; padding: .75rem 1.4rem; border-radius: 8px;
    font-size: .9rem; box-shadow: 0 4px 20px rgba(0,0,0,.5);
    animation: fadeIn .2s ease;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ── Utility: confirm dialog ──────────────────────────────

function confirmAction(message) {
  return window.confirm(message);
}

// ── Auto-hide messages after 4s ─────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.msg.success').forEach(el => {
    setTimeout(() => { el.textContent = ''; }, 4000);
  });
});
