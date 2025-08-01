document.addEventListener('DOMContentLoaded', function () {
  const scanBtn = document.getElementById('scan-btn');
  const statusDiv = document.getElementById('scan-status');
  const proceedContainer = document.getElementById('proceed-container');
  const proceedBtn = document.getElementById('proceed-btn');
  let pollInterval = null;
  let matchedVoterId = null;

  scanBtn.addEventListener('click', function () {
    scanBtn.disabled = true;
    statusDiv.innerHTML = `<div class="text-info">Creating scan trigger...</div>`;
    proceedContainer.style.display = 'none';

    // Clear any existing session to prevent conflicts
    fetch('/api/clear-session/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      }
    }).catch(error => {
      console.log('Session clear failed (non-critical):', error);
    });

    fetch('/api/trigger-scan/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify({ action: 'match' })
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          const triggerId = data.trigger_id;
          statusDiv.innerHTML = `<div class="text-success">Trigger created. Please scan your finger on the device. (Trigger ID: ${triggerId})</div>`;
          startPolling(triggerId);
        } else {
          statusDiv.innerHTML = `<div class="text-danger">Failed to create trigger: ${data.error || data.message || 'Unknown error'}</div>`;
          scanBtn.disabled = false;
        }
      })
      .catch(error => {
        console.error('Fetch error:', error);
        statusDiv.innerHTML = `<div class="text-danger">Error: ${error.message}</div>`;
        scanBtn.disabled = false;
      });
  });

  function startPolling(triggerId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(() => {
      fetch(`/api/scan-result/?trigger_id=${triggerId}`)
        .then(res => res.json())
        .then(data => {
          if (data.status === 'pending') {
            statusDiv.innerHTML = `<div class="text-info">Waiting for fingerprint match...</div>`;
          } else if (data.status === 'success') {
            clearInterval(pollInterval);
            matchedVoterId = data.voter_id;
            statusDiv.innerHTML = `<div class="text-success">Fingerprint matched: ${data.voter_name} (Score: ${data.score.toFixed(2)})</div>`;
            proceedContainer.style.display = 'block';
          } else if (data.status === 'already_voted') {
            clearInterval(pollInterval);
            statusDiv.innerHTML = `<div class="text-warning">Already Voted: ${data.voter_name || 'This voter has already cast their vote'}</div>`;
            scanBtn.disabled = false;
            // Redirect to already voted page after a short delay
            setTimeout(() => {
              window.location.href = '/already-voted/';
            }, 2000);
          } else if (data.status === 'error') {
            clearInterval(pollInterval);
            statusDiv.innerHTML = `<div class="text-danger">No match: ${data.message || 'Fingerprint not registered or unmatched'}</div>`;
            scanBtn.disabled = false;
          } else {
            console.warn('Unknown status from scan result:', data.status);
          }
        })
        .catch(err => {
          console.error('Polling error:', err);
          clearInterval(pollInterval);
          statusDiv.innerHTML = `<div class="text-danger">Error checking scan result: ${err.message}</div>`;
          scanBtn.disabled = false;
        });
    }, 2000);
  }

  proceedBtn.addEventListener('click', function () {
    if (matchedVoterId) {
      window.location.href = `/voter-home/${matchedVoterId}/`;
    }
  }); 

  function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return '';
  }
});
    
    