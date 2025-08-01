// Fingerprint polling for Django admin voter registration
document.addEventListener('DOMContentLoaded', function() {
    const fingerprintField = document.querySelector('.fingerprint-id-field');
    
    if (!fingerprintField) {
        return; // Not on voter creation page
    }
    
    let pollingInterval;
    let lastFingerprintId = null;
    
    // Start polling for fingerprint scans
    function startPolling() {
        pollingInterval = setInterval(pollFingerprint, 2000); // Poll every 2 seconds
        console.log('Started fingerprint polling...');
    }
    
    // Stop polling
    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            console.log('Stopped fingerprint polling.');
        }
    }
    
    // Poll the fingerprint API
    function pollFingerprint() {
        fetch('/api/get-latest-fingerprint/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.fingerprint_id) {
                if (data.fingerprint_id !== lastFingerprintId) {
                    lastFingerprintId = data.fingerprint_id;
                    fingerprintField.value = data.fingerprint_id;
                    fingerprintField.style.backgroundColor = '#d4edda';
                    fingerprintField.style.borderColor = '#c3e6cb';
                    
                    // Show success message
                    showMessage('Fingerprint ID auto-filled: ' + data.fingerprint_id, 'success');
                    
                    // Reset styling after 3 seconds
                    setTimeout(() => {
                        fingerprintField.style.backgroundColor = '';
                        fingerprintField.style.borderColor = '';
                    }, 3000);
                }
            }
        })
        .catch(error => {
            console.error('Error polling fingerprint:', error);
        });
    }
    
    // Show message to user
    function showMessage(message, type) {
        // Remove existing message
        const existingMessage = document.querySelector('.fingerprint-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        // Create new message
        const messageDiv = document.createElement('div');
        messageDiv.className = `fingerprint-message alert alert-${type === 'success' ? 'success' : 'info'}`;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 15px;
            border-radius: 4px;
            color: white;
            font-weight: bold;
            z-index: 9999;
            max-width: 300px;
        `;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        
        // Remove message after 5 seconds
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.remove();
            }
        }, 5000);
    }
    
    // Start polling when page loads
    startPolling();
    
    // Stop polling when user navigates away
    window.addEventListener('beforeunload', stopPolling);
    
    // Stop polling when form is submitted
    const form = fingerprintField.closest('form');
    if (form) {
        form.addEventListener('submit', stopPolling);
    }
    
    // Add visual indicator that polling is active
    const pollingIndicator = document.createElement('div');
    pollingIndicator.innerHTML = `
        <div style="
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #007cba;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 9998;
            display: flex;
            align-items: center;
            gap: 8px;
        ">
            <div style="
                width: 8px;
                height: 8px;
                background: #4CAF50;
                border-radius: 50%;
                animation: pulse 2s infinite;
            "></div>
            Polling for fingerprint...
        </div>
    `;
    
    // Add CSS for pulse animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    document.body.appendChild(pollingIndicator);
}); 