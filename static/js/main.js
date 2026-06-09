document.addEventListener('DOMContentLoaded', function () {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('scheduleFile');
    const browseBtn = document.getElementById('browseBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const uploadResult = document.getElementById('uploadResult');

    const templateUploadZone = document.getElementById('templateUploadZone');
    const templateFileInput = document.getElementById('templateFile');
    const templateBrowseBtn = document.getElementById('templateBrowseBtn');
    const templateUploadProgress = document.getElementById('templateUploadProgress');
    const templateProgressFill = document.getElementById('templateProgressFill');
    const templateProgressText = document.getElementById('templateProgressText');
    const templateUploadResult = document.getElementById('templateUploadResult');

    const trackSelect = document.getElementById('trackSelect');
    const daySelect = document.getElementById('daySelect');
    const downloadTrackBtn = document.getElementById('downloadTrackBtn');
    const downloadDayBtn = document.getElementById('downloadDayBtn');
    const downloadAllBtn = document.getElementById('downloadAllBtn');

    function getCsrfToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    function setupUploadZone(zone, input, browseButton, onUpload) {
        if (!zone || !input) return;

        browseButton.addEventListener('click', (e) => {
            e.stopPropagation();
            input.click();
        });

        zone.addEventListener('click', (e) => {
            if (e.target !== browseButton) input.click();
        });

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                onUpload(e.dataTransfer.files[0]);
            }
        });

        input.addEventListener('change', () => {
            if (input.files.length) onUpload(input.files[0]);
        });
    }

    function postFile(url, fieldName, file, progressEl, fillEl, textEl, resultEl, loadingText) {
        const formData = new FormData();
        formData.append(fieldName, file);

        progressEl.classList.remove('hidden');
        resultEl.classList.add('hidden');
        fillEl.style.width = '30%';
        textEl.textContent = loadingText;

        return fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        })
            .then(res => res.json())
            .then(data => {
                fillEl.style.width = '100%';
                if (data.success) {
                    textEl.textContent = 'Done!';
                    resultEl.className = 'upload-result success';
                    resultEl.textContent = data.message;
                    resultEl.classList.remove('hidden');
                    setTimeout(() => window.location.reload(), 1500);
                } else {
                    textEl.textContent = 'Failed';
                    resultEl.className = 'upload-result error';
                    resultEl.textContent = data.error || 'Upload failed.';
                    resultEl.classList.remove('hidden');
                }
            })
            .catch(err => {
                textEl.textContent = 'Error';
                resultEl.className = 'upload-result error';
                resultEl.textContent = 'Network error: ' + err.message;
                resultEl.classList.remove('hidden');
            });
    }

    setupUploadZone(uploadZone, fileInput, browseBtn, (file) => {
        postFile('/upload/', 'schedule_file', file, uploadProgress, progressFill, progressText, uploadResult, 'Uploading and analyzing...');
    });

    setupUploadZone(templateUploadZone, templateFileInput, templateBrowseBtn, (file) => {
        postFile('/upload/template/', 'template_file', file, templateUploadProgress, templateProgressFill, templateProgressText, templateUploadResult, 'Uploading template...');
    });

    function triggerDownload(url) {
        window.location.href = url;
    }

    if (downloadTrackBtn) {
        downloadTrackBtn.addEventListener('click', () => {
            const track = trackSelect.value;
            if (!track) {
                alert('Please select a track session.');
                return;
            }
            triggerDownload('/download/track/?track=' + encodeURIComponent(track));
        });
    }

    if (downloadDayBtn) {
        downloadDayBtn.addEventListener('click', () => {
            const day = daySelect.value;
            if (!day) {
                alert('Please select a day.');
                return;
            }
            triggerDownload('/download/day/?day=' + encodeURIComponent(day));
        });
    }

    if (downloadAllBtn) {
        downloadAllBtn.addEventListener('click', () => {
            triggerDownload('/download/all/');
        });
    }

    document.querySelectorAll('.track-download-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const track = btn.dataset.track;
            triggerDownload('/download/track/?track=' + encodeURIComponent(track));
        });
    });
});
