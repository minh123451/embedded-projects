// Dashboard logic for Snake Eye AI Monitor

document.addEventListener('DOMContentLoaded', () => {
    const buzzerBtn = document.getElementById('buzzer-btn');
    const buzzerStatus = document.getElementById('buzzer-status-text');
    const totalDetections = document.getElementById('stat-total');
    const lastDetection = document.getElementById('stat-last');
    const streamIframe = document.getElementById('stream-iframe');
    
    // Relay Elements
    const relayBtn = document.getElementById('relay-btn');
    const relayStatus = document.getElementById('relay-status-text');

    let isBuzzerActive = false;
    let isRelayActive = false;

    // Function to update buzzer UI
    function updateBuzzerUI(active) {
        isBuzzerActive = active;
        if (buzzerStatus) {
            buzzerStatus.textContent = active ? 'ON' : 'OFF';
            buzzerStatus.style.color = active ? 'var(--success-color)' : 'var(--danger-color)';
        }

        if (buzzerBtn) {
            const btnText = buzzerBtn.querySelector('.btn-text');
            const btnIcon = buzzerBtn.querySelector('.icon');

            if (active) {
                buzzerBtn.className = 'alarm-btn-on';
                if (btnText) btnText.textContent = 'STOP ALARM';
                if (btnIcon) btnIcon.textContent = '🔕';
            } else {
                buzzerBtn.className = 'alarm-btn-off';
                if (btnText) btnText.textContent = 'START ALARM';
                if (btnIcon) btnIcon.textContent = '🔔';
            }
        }

        // Add pulse effect to the card if active
        const card = document.getElementById('alarm-card');
        if (card) {
            if (active) card.classList.add('pulse-on');
            else card.classList.remove('pulse-on');
        }
    }

    // Function to fetch buzzer state
    async function fetchBuzzerState() {
        try {
            const response = await fetch('/api/buzzer/status');
            const data = await response.json();
            updateBuzzerUI(data.active);
        } catch (error) {
            console.error('Error fetching buzzer status:', error);
        }
    }

    // Function to update relay UI
    function updateRelayUI(active) {
        isRelayActive = active;
        if (relayStatus) {
            relayStatus.textContent = active ? 'ON' : 'OFF';
            relayStatus.style.color = active ? 'var(--success-color)' : 'var(--text-dim)';
        }

        if (relayBtn) {
            const btnText = relayBtn.querySelector('.btn-text');
            const btnIcon = relayBtn.querySelector('.icon');

            if (active) {
                relayBtn.className = 'alarm-btn-on'; // Tạm dùng class on của alarm cho nổi bật
                if (btnText) btnText.textContent = 'TURN OFF';
                if (btnIcon) btnIcon.textContent = '💡';
            } else {
                relayBtn.className = 'alarm-btn-off';
                if (btnText) btnText.textContent = 'TURN ON';
                if (btnIcon) btnIcon.textContent = '💡';
            }
        }
    }

    // Function to fetch relay state
    async function fetchRelayState() {
        try {
            const response = await fetch('/api/relay/status');
            const data = await response.json();
            updateRelayUI(data.active);
        } catch (error) {
            console.error('Error fetching relay status:', error);
        }
    }

    // Function to update stats
    async function updateStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();

            if (totalDetections) totalDetections.textContent = data.total_count;
            if (lastDetection) lastDetection.textContent = data.last_time || 'None';
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }

    // Handle buzzer button click
    if (buzzerBtn) {
        buzzerBtn.addEventListener('click', async () => {
            const endpoint = isBuzzerActive ? '/buzzer/off' : '/buzzer/on';
            try {
                // Optimistic UI update
                updateBuzzerUI(!isBuzzerActive);
                await fetch(endpoint);
                fetchBuzzerState(); // Sync with server
            } catch (error) {
                console.error('Error toggling buzzer:', error);
            }
        });
    }

    // Handle relay button click
    if (relayBtn) {
        relayBtn.addEventListener('click', async () => {
            const endpoint = isRelayActive ? '/relay/off' : '/relay/on';
            try {
                // Optimistic UI update
                updateRelayUI(!isRelayActive);
                await fetch(endpoint);
                fetchRelayState(); // Sync with server
            } catch (error) {
                console.error('Error toggling relay:', error);
            }
        });
    }

    // Handle stream reload
    window.reloadStream = () => {
        if (streamIframe) {
            const currentSrc = streamIframe.src;
            streamIframe.src = '';
            setTimeout(() => {
                streamIframe.src = currentSrc;
            }, 100);
        }
    }

    // Handle deletion
    window.deleteIntrusion = async (filename, elementId) => {
        if (!confirm('Bạn có chắc chắn muốn xóa ảnh này không?')) return;

        try {
            const response = await fetch(`/api/delete/${filename}`, { method: 'DELETE' });
            if (response.ok) {
                const element = document.getElementById(elementId);
                if (element) {
                    element.style.opacity = '0';
                    setTimeout(() => element.remove(), 300);
                }
                updateStats();
            } else {
                alert('Xóa thất bại. Vui lòng thử lại.');
            }
        } catch (error) {
            console.error('Error deleting image:', error);
        }
    }

    // Initial load and periodic updates
    fetchBuzzerState();
    fetchRelayState();
    updateStats();
    setInterval(fetchBuzzerState, 1000); // Poll every 1 seconds
    setInterval(fetchRelayState, 1500);  // Poll relay every 1.5 seconds
    setInterval(updateStats, 10000);    // Poll stats every 10 seconds
});
