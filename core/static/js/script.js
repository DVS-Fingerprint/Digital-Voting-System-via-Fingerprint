// script.js - Voting System UI Logic

document.addEventListener('DOMContentLoaded', function() {
  // Countdown Timer (for dashboard.html)
  const timerEl = document.getElementById('countdown-timer');
  if (timerEl) {
    let seconds = window.sessionCountdown || 300; // Default 5 min
    function updateTimer() {
      const min = String(Math.floor(seconds / 60)).padStart(2, '0');
      const sec = String(seconds % 60).padStart(2, '0');
      timerEl.textContent = `${min}:${sec}`;
      if (seconds > 0) seconds--;
    }
    updateTimer();
    setInterval(updateTimer, 1000);
  }

  // Modal confirmation for vote submission
  const confirmBtn = document.getElementById('confirmVoteBtn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', function() {
      document.getElementById('voteForm').submit();
    });
  }

  // Toast notification utility
  window.showToast = function(message, type='info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = message;
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, 3500);
  };

  // Fingerprint scan simulation (scanner.html)
  const scanStatus = document.getElementById('scan-status');
  if (scanStatus) {
    setTimeout(() => {
      scanStatus.querySelector('.lead').textContent = window.gettext ? window.gettext('Verifying...') : 'Verifying...';
      setTimeout(() => {
        scanStatus.querySelector('.lead').textContent = window.gettext ? window.gettext('Scan successful!') : 'Scan successful!';
        scanStatus.querySelector('.pulse-animation').style.background = '#22c55e';
        setTimeout(() => {
          window.location.href = '/dashboard/';
        }, 1200);
      }, 1800);
    }, 1800);
  }

  // Language switcher (auto-submit handled by form)
}); 