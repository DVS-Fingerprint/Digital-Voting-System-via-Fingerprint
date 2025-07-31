document.addEventListener('DOMContentLoaded', function () {
    const startScanBtn = document.getElementById('startScanBtn');
    const currentVoterId = document.getElementById('voter_id_field')?.value;

    startScanBtn.addEventListener('click', function () {
        console.log('🔘 Start Scan Button clicked');
        if (!currentVoterId) {
            alert("Voter ID not found.");
            return;
        }

        console.log('🔍 Triggering scan for voter_id:', currentVoterId);

        fetch('/api/trigger-scan/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                voter_id: currentVoterId,
                action: 'register'
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('✅ Trigger response:', data);
            alert('Scan trigger sent successfully!');
            updateTemplateDropdown();  // 🔄 refresh the dropdown after scan
        })
        .catch(error => {
            console.error('❌ Trigger error:', error);
            alert('Failed to trigger scan.');
        });
    });

    function updateTemplateDropdown() {
    fetch('/api/get-pending-templates/')
        .then(response => response.json())
        .then(data => {
            const dropdown = document.getElementById('id_template_hex');
            const registerBtn = document.getElementById('registerBtn');
            if (!dropdown) return;

            dropdown.innerHTML = '';

            const defaultOption = document.createElement('option');
            defaultOption.textContent = '---------';
            defaultOption.value = '';
            dropdown.appendChild(defaultOption);

            data.forEach(template => {
                const option = document.createElement('option');
                option.value = template.id;
                option.textContent = `Template ${template.id}`;
                dropdown.appendChild(option);
            });

            if (registerBtn) {
                registerBtn.disabled = data.length === 0;
            }
        })
        .catch(err => {
            console.error('Failed to update templates:', err);
        });
}

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
