document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const menuToggle = document.getElementById('menuToggle');
    const sidebarClose = document.getElementById('sidebarClose');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (sidebarOverlay) sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (sidebarOverlay) sidebarOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (menuToggle) menuToggle.addEventListener('click', openSidebar);
    if (sidebarClose) sidebarClose.addEventListener('click', closeSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

    document.querySelectorAll('.sidebar-nav .nav-item').forEach(function (link) {
        link.addEventListener('click', function () {
            if (window.innerWidth <= 768) closeSidebar();
        });
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > 768) closeSidebar();
    });

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
    const trackDutyDaySelect = document.getElementById('trackDutyDaySelect');
    const downloadTrackDutyBtn = document.getElementById('downloadTrackDutyBtn');
    const downloadTrackDutyAllBtn = document.getElementById('downloadTrackDutyAllBtn');

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? decodeURIComponent(cookie.split('=')[1].trim()) : '';
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

    function resetUploadProgress(progressEl, fillEl, textEl) {
        fillEl.style.width = '0%';
        if (textEl) textEl.textContent = '';
        progressEl.classList.add('hidden');
    }

    function postFile(url, fieldName, file, progressEl, fillEl, textEl, resultEl, loadingText) {
        const formData = new FormData();
        formData.append(fieldName, file);
        const csrfToken = getCsrfToken();

        if (!csrfToken) {
            resultEl.className = 'upload-result error';
            resultEl.textContent = 'Session expired. Please refresh the page and login again.';
            resultEl.classList.remove('hidden');
            return Promise.resolve();
        }

        progressEl.classList.remove('hidden');
        resultEl.classList.add('hidden');
        fillEl.style.width = '35%';
        if (textEl) textEl.textContent = loadingText;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000);

        return fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData,
            credentials: 'same-origin',
            signal: controller.signal,
        })
            .then(async (res) => {
                clearTimeout(timeoutId);
                fillEl.style.width = '85%';

                const contentType = res.headers.get('content-type') || '';
                let data = null;
                if (contentType.includes('application/json')) {
                    data = await res.json();
                }

                if (!data) {
                    throw new Error(
                        res.status === 403
                            ? 'Permission denied. Refresh the page and try again.'
                            : `Server error (${res.status}). Check Web error log on PythonAnywhere.`
                    );
                }

                fillEl.style.width = '100%';
                if (res.ok && data.success) {
                    if (textEl) textEl.textContent = 'Done!';
                    resultEl.className = 'upload-result success';
                    resultEl.textContent = data.message;
                    resultEl.classList.remove('hidden');
                    setTimeout(() => {
                        resetUploadProgress(progressEl, fillEl, textEl);
                        window.location.reload();
                    }, 1200);
                } else {
                    resetUploadProgress(progressEl, fillEl, textEl);
                    resultEl.className = 'upload-result error';
                    resultEl.textContent = data.error || 'Upload failed.';
                    resultEl.classList.remove('hidden');
                }
            })
            .catch(err => {
                clearTimeout(timeoutId);
                resetUploadProgress(progressEl, fillEl, textEl);
                resultEl.className = 'upload-result error';
                if (err.name === 'AbortError') {
                    resultEl.textContent = 'Upload timed out. Try a smaller file or reload the page.';
                } else {
                    resultEl.textContent = err.message || 'Network error during upload.';
                }
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

    if (downloadTrackDutyBtn) {
        downloadTrackDutyBtn.addEventListener('click', () => {
            const day = trackDutyDaySelect.value;
            if (!day) {
                alert('Please select a day for track duty download.');
                return;
            }
            triggerDownload('/download/track-duty/?day=' + encodeURIComponent(day));
        });
    }

    if (downloadTrackDutyAllBtn) {
        downloadTrackDutyAllBtn.addEventListener('click', () => {
            triggerDownload('/download/track-duty/');
        });
    }

    document.querySelectorAll('.track-download-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const track = btn.dataset.track;
            triggerDownload('/download/track/?track=' + encodeURIComponent(track));
        });
    });

    const verifierUploadZone = document.getElementById('verifierUploadZone');
    const verifierFileInput = document.getElementById('verifierFile');
    const verifierBrowseBtn = document.getElementById('verifierBrowseBtn');
    const verifierUploadProgress = document.getElementById('verifierUploadProgress');
    const verifierProgressFill = document.getElementById('verifierProgressFill');
    const verifierProgressText = document.getElementById('verifierProgressText');
    const verifierUploadResult = document.getElementById('verifierUploadResult');

    if (verifierUploadZone && verifierFileInput) {
        setupUploadZone(verifierUploadZone, verifierFileInput, verifierBrowseBtn, (file) => {
            postFile('/upload/verifier/', 'verifier_file', file, verifierUploadProgress, verifierProgressFill, verifierProgressText, verifierUploadResult, 'Assigning verifiers...');
        });
    }
});
