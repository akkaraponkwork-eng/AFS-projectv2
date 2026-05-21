// --- Live Clock Logic ---
function updateClock() {
    const timeEl = document.getElementById('liveTime');
    const dateEl = document.getElementById('liveDate');
    if (!timeEl || !dateEl) return;
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const dateStr = now.toLocaleDateString('th-TH', { year: 'numeric', month: 'short', day: 'numeric', weekday: 'short' });
    
    timeEl.textContent = timeStr;
    dateEl.textContent = dateStr;
}
setInterval(updateClock, 1000);
updateClock(); // Initial call
// -----------------------

document.getElementById('automationForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    // UI Elements
    const submitBtn = document.getElementById('submitBtn');
    const stopBtn = document.getElementById('stopBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.spinner');
    const statusBox = document.getElementById('statusBox');
    const statusTitle = document.getElementById('statusTitle');
    const statusMessage = document.getElementById('statusMessage');
    const successIcon = document.querySelector('.success-icon');
    const errorIcon = document.querySelector('.error-icon');
    const pulseDot = document.querySelector('.pulse-dot');
    const logContainer = document.getElementById('logContainer');
    
    // Get form values
    const startRow = document.getElementById('startRow').value;
    const endRow = document.getElementById('endRow').value;
    const tempMin = document.getElementById('tempMin').value;
    const tempMax = document.getElementById('tempMax').value;
    const timePeriod = document.getElementById('timePeriod').value;
    const uValue = document.getElementById('uValue').value;
    const showBrowser = document.getElementById('showBrowser').checked;
    
    // Update UI for loading state
    submitBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');
    stopBtn.disabled = false;
    
    statusBox.classList.remove('hidden');
    successIcon.classList.add('hidden');
    errorIcon.classList.add('hidden');
    if (pulseDot) pulseDot.classList.remove('hidden');
    
    logContainer.style.display = 'block';
    logContainer.innerHTML = '<div>เชื่อมต่อกับเซิร์ฟเวอร์...</div>';
    
    // เลื่อนหน้าจอลงมาที่กล่องสถานะอัตโนมัติ
    setTimeout(() => {
        statusBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
    
    statusTitle.textContent = 'กำลังทำงาน';
    statusMessage.textContent = 'โปรดรอจนกว่าจะขึ้นสถานะเสร็จสมบูรณ์...';
    statusTitle.style.color = '#3b82f6';
    
    // Construct URL for EventSource
    const url = `/api/start?startRow=${startRow}&endRow=${endRow}&tempMin=${tempMin}&tempMax=${tempMax}&timePeriod=${timePeriod}&showBrowser=${showBrowser}&uValue=${uValue}`;
    
    const eventSource = new EventSource(url);
    
    // Handle Stop Button
    stopBtn.onclick = function() {
        stopBtn.disabled = true;
        stopBtn.querySelector('.btn-text').textContent = 'กำลังยกเลิก...';
        fetch('/api/stop', { method: 'POST' })
            .catch(err => console.error('Error stopping:', err));
    };
    
    function resetButtons() {
        stopBtn.classList.add('hidden');
        submitBtn.classList.remove('hidden');
        submitBtn.disabled = false;
        btnText.textContent = 'เริ่มการทำงานใหม่';
        spinner.classList.add('hidden');
        stopBtn.querySelector('.btn-text').textContent = 'ยกเลิกการทำงาน';
        if (pulseDot) pulseDot.classList.add('hidden');
    }

    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            
            // Append log
            const logEntry = document.createElement('div');
            logEntry.style.marginBottom = '4px';
            
            if (data.type === 'error') {
                logEntry.style.color = '#ef4444';
            } else if (data.type === 'success') {
                logEntry.style.color = '#10b981';
            } else if (data.type === 'warning') {
                logEntry.style.color = '#eab308';
            }
            
            logEntry.textContent = `> ${data.message}`;
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
            
            // Handle completion or error
            if (data.type === 'success' || data.type === 'error') {
                eventSource.close();
                resetButtons();
                
                if (data.type === 'success') {
                    successIcon.classList.remove('hidden');
                    statusTitle.textContent = 'เสร็จสิ้น!';
                    statusTitle.style.color = '#10b981';
                    statusMessage.textContent = 'กระบวนการทำงานจบลงแล้ว';
                } else {
                    errorIcon.classList.remove('hidden');
                    statusTitle.textContent = 'เกิดข้อผิดพลาด';
                    statusTitle.style.color = '#ef4444';
                    statusMessage.textContent = 'ระบบหยุดทำงาน';
                }
            }
        } catch (e) {
            console.error('Error parsing SSE data', e);
        }
    };
    
    eventSource.onerror = function(err) {
        console.error('SSE Error', err);
        eventSource.close();
        
        // Reset UI if it errors out before success/error message
        if (!submitBtn.classList.contains('hidden') === false) { // if submitBtn is currently hidden
            errorIcon.classList.remove('hidden');
            statusTitle.textContent = 'ขาดการเชื่อมต่อ';
            statusTitle.style.color = '#ef4444';
            statusMessage.textContent = 'ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้';
            
            resetButtons();
        }
    };
});
