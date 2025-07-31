document.addEventListener('DOMContentLoaded', function() {
    const scanBtn = document.getElementById('scan-btn');
    const statusDiv = document.getElementById('scan-status');
    const proceedContainer = document.getElementById('proceed-container');
    const proceedBtn = document.getElementById('proceed-btn');
    let isScanning = false;

    scanBtn.addEventListener('click', function() {
        if (isScanning) return;
        isScanning = true;
        
        scanBtn.disabled = true;
        statusDiv.innerHTML = '<div class="text-info">Waiting for scanner...</div>';
        proceedContainer.style.display = 'none';

        // Simulate fingerprint scanning
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 25;
            statusDiv.innerHTML = `<div class="text-info">Scanning... (${progress}%)</div>`;

            if (progress >= 100) {
                clearInterval(progressInterval);
                statusDiv.innerHTML = '<div class="text-info">Verifying...</div>';
                
                // Simulate fingerprint verification
                setTimeout(() => {
                    verifyFingerprint();
                }, 1000);
            }
        }, 800);
    });

    // Function to verify fingerprint with backend using fingerprint verification endpoint
    function verifyFingerprint() {
        // In a real scenario, this would get the fingerprint template from ESP32
        // For demo purposes, we'll simulate with a test fingerprint_id
        // In production, this would be the actual fingerprint_id from ESP32
        const testFingerprintId = 'F123456'; // Replace with actual ESP32 fingerprint_id data
        
        fetch('/voting/api/fingerprint-verification/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                fingerprint_id: testFingerprintId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'verified') {
                statusDiv.innerHTML = `<div class="text-success">Welcome, ${data.voter_name}! Redirecting to voting...</div>`;
                
                // Set session for authenticated voter
                setTimeout(() => {
                    window.location.href = '/voting/cast-vote/';
                }, 1500);
                
            } else if (data.status === 'already_voted') {
                statusDiv.innerHTML = `<div class="text-warning">Hello ${data.voter_name}, you have already voted.</div>`;
                
                setTimeout(() => {
                    window.location.href = '/voting/already-voted/';
                }, 2000);
                
            } else if (data.status === 'not_found') {
                statusDiv.innerHTML = '<div class="text-danger">Fingerprint not recognized. Please contact administrator.</div>';
                isScanning = false;
                scanBtn.disabled = false;
                
            } else if (data.status === 'no_session') {
                statusDiv.innerHTML = '<div class="text-warning">Voting is not currently active. Please try again later.</div>';
                isScanning = false;
                scanBtn.disabled = false;
                
            } else {
                statusDiv.innerHTML = '<div class="text-danger">Verification failed. Please try again.</div>';
                isScanning = false;
                scanBtn.disabled = false;
            }
        })
        .catch(error => {
            statusDiv.innerHTML = '<div class="text-danger">Connection error. Please try again.</div>';
            console.error('Error:', error);
            isScanning = false;
            scanBtn.disabled = false;
        });
    }

    // Add manual retry functionality
    const retryButton = document.createElement('button');
    retryButton.className = 'btn btn-outline-primary mt-3';
    retryButton.innerHTML = '<i class="fas fa-redo me-2"></i>Retry Scan';
    retryButton.style.display = 'none';
    retryButton.onclick = function() {
        isScanning = false;
        scanBtn.disabled = false;
        statusDiv.innerHTML = '';
        proceedContainer.style.display = 'none';
        this.style.display = 'none';
    };
    
    statusDiv.appendChild(retryButton);

    // Show retry button after error
    setTimeout(() => {
        if (statusDiv.innerHTML.includes('error') || statusDiv.innerHTML.includes('failed')) {
            retryButton.style.display = 'block';
        }
    }, 5000);

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
