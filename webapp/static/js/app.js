// GPX Scaler Web App JavaScript

class GPXScalerApp {
    // Add a lock to prevent concurrent updateUploadedFilesList calls
    _updatingFilesList = false;
    constructor() {
        this.uploadedFiles = new Map();
        this.selectedFileId = null;
        this.processedFiles = new Map();
        this.originalElevationChart = null;
        this.scaledElevationChart = null;
        this.originalMap = null;
        this.scaledMap = null;
        this.originalLayer = null;
        this.scaledLayer = null;

        this.loadSavedParameters();
        this.initializeEventListeners();
        this.initializeCharts();
        this.initializeMaps();
    }

    initializeMaps() {
        // Assumes Leaflet.js is loaded and map containers exist
        const originalMapElem = document.getElementById('originalRouteMap');
        const scaledMapElem = document.getElementById('scaledRouteMap');
        if (!originalMapElem || !scaledMapElem) return;

        // Set map container height if needed
        originalMapElem.style.height = '260px';
        scaledMapElem.style.height = '260px';

        // Initialize maps
        this.originalMap = L.map(originalMapElem, {
            zoomControl: false,
            attributionControl: false
        }).setView([52.5, 4.0], 10);
        this.scaledMap = L.map(scaledMapElem, {
            zoomControl: false,
            attributionControl: false
        }).setView([52.5, 4.0], 10);

        // Add tile layers
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.originalMap);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.scaledMap);

        // Add route layers
        this.originalLayer = L.layerGroup().addTo(this.originalMap);
        this.scaledLayer = L.layerGroup().addTo(this.scaledMap);
    }

    initializeCharts() {
        // Assumes Chart.js is loaded and canvas elements exist
        const originalCtx = document.getElementById('originalElevationChart').getContext('2d');
        const scaledCtx = document.getElementById('scaledElevationChart').getContext('2d');
        this.originalElevationChart = new Chart(originalCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Elevation (m)',
                    data: [],
                    borderColor: '#6c757d',
                    backgroundColor: 'rgba(108,117,125,0.1)',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Elevation (m)',
                            font: {
                                family: 'Inter, Segoe UI, Arial, sans-serif',
                                size: 13,
                                weight: '400',
                                style: 'normal'
                            },
                            color: '#333',
                            padding: {top: 8, bottom: 0}
                        },
                        ticks: {
                            font: {
                                family: 'Inter, Segoe UI, Arial, sans-serif',
                                size: 12,
                                weight: '400',
                                style: 'normal'
                            },
                            color: '#333'
                        }
                    }
                }
            }
        });
        this.scaledElevationChart = new Chart(scaledCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Elevation (m)',
                    data: [],
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13,110,253,0.1)',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Elevation (m)',
                            font: {
                                family: 'Inter, Segoe UI, Arial, sans-serif',
                                size: 13,
                                weight: '400',
                                style: 'normal'
                            },
                            color: '#333',
                            padding: {top: 8, bottom: 0}
                        },
                        ticks: {
                            font: {
                                family: 'Inter, Segoe UI, Arial, sans-serif',
                                size: 12,
                                weight: '400',
                                style: 'normal'
                            },
                            color: '#333'
                        }
                    }
                }
            }
        });
    }

    // ...existing code...

    loadSavedParameters() {
        try {
            // Load saved parameters from localStorage
            const savedParams = localStorage.getItem('gpxScalerParams');
            if (savedParams) {
                const params = JSON.parse(savedParams);

                // Set form values if elements exist
                if (params.distanceScale && document.getElementById('distanceScale')) {
                    document.getElementById('distanceScale').value = params.distanceScale;
                }
                if (params.ascentScale && document.getElementById('ascentScale')) {
                    document.getElementById('ascentScale').value = params.ascentScale;
                }
                if (params.startLat && document.getElementById('startLat')) {
                    document.getElementById('startLat').value = params.startLat;
                }
                if (params.startLon && document.getElementById('startLon')) {
                    document.getElementById('startLon').value = params.startLon;
                }
                if (params.baseName && document.getElementById('baseName')) {
                    document.getElementById('baseName').value = params.baseName;
                }
                if (params.outputFormat && document.getElementById('outputFormat')) {
                    document.getElementById('outputFormat').value = params.outputFormat;
                }
                if (params.addTiming !== undefined && document.getElementById('addTiming')) {
                    document.getElementById('addTiming').checked = params.addTiming;
                    this.toggleTimingControls();
                }
                if (params.powerWatts && document.getElementById('powerWatts')) {
                    document.getElementById('powerWatts').value = params.powerWatts;
                }
                if (params.weightKg && document.getElementById('weightKg')) {
                    document.getElementById('weightKg').value = params.weightKg;
                }
                // Always sync display and trigger preview after loading
                this.updateScaleValues();
            }
        } catch (error) {
            console.log('Could not load saved parameters:', error);
        }
    }

    saveParameters() {
        try {
            const params = {
                distanceScale: document.getElementById('distanceScale')?.value,
                ascentScale: document.getElementById('ascentScale')?.value,
                startLat: document.getElementById('startLat')?.value,
                startLon: document.getElementById('startLon')?.value,
                baseName: document.getElementById('baseName')?.value,
                outputFormat: document.getElementById('outputFormat')?.value,
                addTiming: document.getElementById('addTiming')?.checked,
                powerWatts: document.getElementById('powerWatts')?.value,
                weightKg: document.getElementById('weightKg')?.value
            };
            localStorage.setItem('gpxScalerParams', JSON.stringify(params));
        } catch (error) {
            console.log('Could not save parameters:', error);
        }
    }

    initializeEventListeners() {
        // ...reverted parameter-saving event listeners...
        // Live update for all relevant controls
        const startLat = document.getElementById('startLat');
        const startLon = document.getElementById('startLon');
        const baseName = document.getElementById('baseName');
        const outputFormat = document.getElementById('outputFormat');
        const addTiming = document.getElementById('addTiming');
        const powerWatts = document.getElementById('powerWatts');
        const weightKg = document.getElementById('weightKg');

        if (startLat) startLat.addEventListener('input', () => {
            this.saveParameters();
            this.updatePreview();
        });
        if (startLon) startLon.addEventListener('input', () => {
            this.saveParameters();
            this.updatePreview();
        });
        if (baseName) baseName.addEventListener('input', () => {
            this.saveParameters();
            this.updatePreview();
        });
        if (outputFormat) outputFormat.addEventListener('change', () => {
            this.saveParameters();
            this.updatePreview();
        });
        if (addTiming) addTiming.addEventListener('change', () => {
            this.saveParameters();
            this.toggleTimingControls();
            this.updatePreview();
        });
        if (powerWatts) powerWatts.addEventListener('input', () => {
            this.saveParameters();
            this.updatePreview();
        });
        if (weightKg) weightKg.addEventListener('input', () => {
            this.saveParameters();
            this.updatePreview();
        });
        // File upload events
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');

        // Reduce drop zone height via inline style (for immediate effect)
        if (dropZone) {
            dropZone.style.height = '60px'; // or adjust as needed
            dropZone.style.minHeight = '40px';
            dropZone.style.maxHeight = '80px';
            dropZone.style.padding = '0';
            dropZone.style.margin = '0';
            dropZone.style.overflow = 'hidden';
        }

        // Remove internal spacing from children of dropZone
        if (dropZone) {
            Array.from(dropZone.children).forEach(child => {
                child.style.padding = '0';
                child.style.margin = '0';
                child.style.boxSizing = 'border-box';
            });
        }

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            if (files.length > 0) {
                this.uploadFiles(files);
            }
        });
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                this.uploadFiles(files);
            }
        });

        // Scale slider events
        const distanceScale = document.getElementById('distanceScale');
        const ascentScale = document.getElementById('ascentScale');
        if (distanceScale) {
            distanceScale.addEventListener('input', () => {
                this.saveParameters();
                this.updateScaleValues();
            });
        }
        if (ascentScale) {
            ascentScale.addEventListener('input', () => {
                this.saveParameters();
                this.updateScaleValues();
            });
        }

        // Process All Files button event
        const processAllBtn = document.getElementById('processAllBtn');
        if (processAllBtn) {
            processAllBtn.addEventListener('click', () => this.processAllFiles());
        }
    }

    async uploadFiles(files) {
        // Show upload progress area, hide drop zone
        const dropZone = document.getElementById('dropZone');
        const uploadProgressArea = document.getElementById('uploadProgressArea');
        if (dropZone) dropZone.style.display = 'none';
        if (uploadProgressArea) uploadProgressArea.style.display = 'block';

        this.initializeUploadProgressBars(files);

        // Upload all files in a single FormData as 'files'[]
        const formData = new FormData();
        files.forEach((file, index) => {
            if (file instanceof File) {
                formData.append('files', file);
                console.log('[DEBUG] Appending file as files:', file.name, file.type, file.size);
            } else {
                console.error('[DEBUG] Not a File object:', file);
            }
        });
        // Debug: log FormData keys and values
        for (let pair of formData.entries()) {
            console.log('[DEBUG] FormData:', pair[0], pair[1]);
        }
        const uploadPromise = new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/upload');
            // Do NOT set any custom headers here, let the browser set Content-Type for FormData
            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    this.updateUploadFileProgress(0, percentComplete, 'info', 'Uploading...');
                }
            };
            xhr.onload = () => {
                console.log('[DEBUG] Upload response:', xhr.status, xhr.statusText, xhr.responseText);
                if (xhr.status === 200) {
                    try {
                        const result = JSON.parse(xhr.responseText);
                        resolve(result);
                    } catch (error) {
                        reject(new Error('Invalid response format'));
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText} - ${xhr.responseText}`));
                }
            };
            xhr.onerror = () => {
                reject(new Error('Network error occurred'));
            };
            xhr.send(formData);
        });
        const uploadPromises = [uploadPromise];

        try {
            const results = await Promise.all(uploadPromises);
            // Debug: log backend results
            console.log('[DEBUG] Upload results:', results);
            // The backend returns an object with 'files': [ ... ]
            results.forEach((result) => {
                console.log('[DEBUG] Processing result:', result);
                if (result.success && Array.isArray(result.files)) {
                    result.files.forEach(fileObj => {
                        console.log('[DEBUG] File object:', fileObj);
                        if (fileObj.id) {
                            this.uploadedFiles.set(fileObj.id, {
                                filename: fileObj.filename,
                                distance: fileObj.distance,
                                ascent: fileObj.ascent,
                                timingData: null
                            });
                        }
                    });
                }
            });
            console.log('[DEBUG] uploadedFiles map after upload:', Array.from(this.uploadedFiles.entries()));
            this.updateUploadedFilesList();
            this.updateProcessButton();
            // Automatically select the first file after upload if any
            if (this.uploadedFiles.size > 0) {
                const firstId = Array.from(this.uploadedFiles.keys())[0];
                this.selectFile(firstId);
            }
        } catch (error) {
            // If error contains response text, show it for debugging
            let errorMsg = error.message;
            if (error && error.responseText) {
                errorMsg += '\nServer response: ' + error.responseText;
            }
            this.showError('Upload failed: ' + errorMsg);
        } finally {
            // Hide upload progress area, show drop zone
            if (dropZone) dropZone.style.display = '';
            if (uploadProgressArea) uploadProgressArea.style.display = 'none';
        }
    }
    calculateScaledValues(originalDistance, originalAscent) {
        const distanceScale = parseFloat(document.getElementById('distanceScale').value);
        const ascentScale = parseFloat(document.getElementById('ascentScale').value);

        const scaledDistance = originalDistance * distanceScale;
        const scaledAscent = originalAscent * ascentScale;

        // Physics-based cycling time estimation
        const addTiming = document.getElementById('addTiming').checked;
        let scaledDuration = null;

        if (addTiming) {
            // Sensible defaults
            const power = parseFloat(document.getElementById('powerWatts')?.value) || 200; // Watts
            const weight = parseFloat(document.getElementById('weightKg')?.value) || 75; // kg (rider + bike)
            const g = 9.81; // gravity
            const Cr = 0.005; // rolling resistance
            const CdA = 0.3; // drag area
            const rho = 1.225; // air density
            const wind = 0; // m/s

            // Assume route is split into ascent and flat for estimation
            // Flat distance (km)
            const flatDistance = scaledDistance - (scaledAscent / 1000); // km
            const ascentDistance = scaledAscent / 1000; // km

            // Helper to estimate speed for a segment
            function estimateSpeed(power, weight, gradient) {
                // Solve for v in: P = (Cr*m*g*v) + (0.5*CdA*rho*v^3) + (m*g*sin(theta)*v)
                // For small gradients, sin(theta) ~ gradient
                // Use Newton's method for v
                let v = 8; // initial guess (m/s)
                for (let i = 0; i < 10; i++) {
                    const rolling = Cr * weight * g * v;
                    const air = 0.5 * CdA * rho * Math.pow(v + wind, 3);
                    const gravity = weight * g * gradient * v;
                    const f = rolling + air + gravity - power;
                    // Derivative wrt v
                    const df = Cr * weight * g + 1.5 * CdA * rho * Math.pow(v + wind, 2) + weight * g * gradient;
                    v = v - f / df;
                    if (v < 1) v = 1; // don't allow negative/zero speed
                }
                return v; // m/s
            }

            // Estimate time for ascent
            const ascentGradient = scaledAscent / (ascentDistance * 1000); // total ascent over ascent distance
            const ascentSpeed = estimateSpeed(power, weight, ascentGradient);
            const ascentTime = ascentDistance * 1000 / ascentSpeed; // seconds

            // Estimate time for flat
            const flatSpeed = estimateSpeed(power, weight, 0);
            const flatTime = flatDistance * 1000 / flatSpeed; // seconds

            // Total time in hours
            scaledDuration = (ascentTime + flatTime) / 3600;
        }

        return {
            distance: scaledDistance,
            ascent: scaledAscent,
            duration: scaledDuration
        };
    }

    async updateUploadedFilesList() {
        if (this._updatingFilesList) return;
        this._updatingFilesList = true;
        try {
            const container = document.getElementById('uploadedFiles');
            if (!container) {
                alert('Error: The file list container with id="uploadedFiles" is missing from the HTML.');
                this._updatingFilesList = false;
                return;
            }
            container.style.display = '';
            container.style.visibility = 'visible';
            const prevScroll = container.scrollTop || 0;
            container.style.minHeight = '90px';
            container.style.maxHeight = '180px';
            container.style.overflowY = 'scroll';

            // If no files, show placeholder and return
            if (this.uploadedFiles.size === 0) {
                container.innerHTML = '<div id="fileCardPlaceholder" style="height:60px;opacity:0.2;">No files uploaded</div>';
                this._updatingFilesList = false;
                return;
            }

            // Otherwise, render file cards
            container.innerHTML = '';
            const distanceScale = parseFloat(document.getElementById('distanceScale').value);
            const ascentScale = parseFloat(document.getElementById('ascentScale').value);
            const addTiming = document.getElementById('addTiming').checked;
            const powerWatts = addTiming ? document.getElementById('powerWatts').value : null;
            const weightKg = addTiming ? document.getElementById('weightKg').value : null;

            // For each file, fetch timing data from backend if timing is enabled
            const fetchTimingPromises = Array.from(this.uploadedFiles.entries()).map(async ([fileId, file]) => {
                if (addTiming) {
                    let url = `/preview_scaled/${fileId}?distance_scale=${distanceScale}&ascent_scale=${ascentScale}`;
                    url += `&start_lat=0&start_lon=0`;
                    url += `&power_watts=${powerWatts}&weight_kg=${weightKg}`;
                    try {
                        const response = await fetch(url);
                        const result = await response.json();
                        if (result.success && result.timing) {
                            file.timingData = result.timing;
                        }
                    } catch (e) {
                        // Ignore errors, fallback to local calculation
                    }
                } else {
                    file.timingData = null;
                }
            });
            await Promise.all(fetchTimingPromises);

            for (const [fileId, file] of this.uploadedFiles.entries()) {
                const scaledDistance = file.distance * distanceScale;
                const scaledAscent = file.ascent * ascentScale;
                let scaledDurationHours = null;
                let originalDurationHours = null;
                if (file.timingData && file.timingData.scaled_duration_hours) {
                    scaledDurationHours = file.timingData.scaled_duration_hours;
                }
                if (addTiming) {
                    const power = parseFloat(document.getElementById('powerWatts')?.value) || 200;
                    const weight = parseFloat(document.getElementById('weightKg')?.value) || 75;
                    const g = 9.81;
                    const Cr = 0.005;
                    const CdA = 0.3;
                    const rho = 1.225;
                    const wind = 0;
                    const originalDistance = file.distance;
                    const originalAscent = file.ascent;
                    const flatDistanceOrig = originalDistance - (originalAscent / 1000);
                    const ascentDistanceOrig = originalAscent / 1000;
                    function estimateSpeed(power, weight, gradient) {
                        let v = 8;
                        for (let i = 0; i < 10; i++) {
                            const rolling = Cr * weight * g * v;
                            const air = 0.5 * CdA * rho * Math.pow(v + wind, 3);
                            const gravity = weight * g * gradient * v;
                            const f = rolling + air + gravity - power;
                            const df = Cr * weight * g + 1.5 * CdA * rho * Math.pow(v + wind, 2) + weight * g * gradient;
                            v = v - f / df;
                            if (v < 1) v = 1;
                        }
                        return v;
                    }
                    const ascentGradientOrig = originalAscent / (ascentDistanceOrig * 1000);
                    const ascentSpeedOrig = estimateSpeed(power, weight, ascentGradientOrig);
                    const ascentTimeOrig = ascentDistanceOrig * 1000 / ascentSpeedOrig;
                    const flatSpeedOrig = estimateSpeed(power, weight, 0);
                    const flatTimeOrig = flatDistanceOrig * 1000 / flatSpeedOrig;
                    originalDurationHours = (ascentTimeOrig + flatTimeOrig) / 3600;
                }
                let originalDurationBadge = '';
                let scaledDurationBadge = '';
                if (originalDurationHours) {
                    const hours = Math.floor(originalDurationHours);
                    const minutes = Math.round((originalDurationHours - hours) * 60);
                    originalDurationBadge = `<span class="badge bg-secondary me-1" title="Original Duration">${hours}h ${minutes}m</span>`;
                }
                if (scaledDurationHours) {
                    const hours = Math.floor(scaledDurationHours);
                    const minutes = Math.round((scaledDurationHours - hours) * 60);
                    scaledDurationBadge = `<span class="badge bg-info me-1" title="Scaled Duration">${hours}h ${minutes}m</span>`;
                }
                const fileElement = document.createElement('div');
                fileElement.className = `file-item ${fileId === this.selectedFileId ? 'selected' : ''}`;
                fileElement.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="fw-bold">${file.filename}</span>
                        <span class="d-flex align-items-center">
                            <i class="fas fa-eye me-2"></i>
                            <button class="btn btn-sm btn-outline-danger remove-file-btn" title="Remove file" style="padding:0.25rem 0.5rem;display:inline-flex;align-items:center;">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </span>
                    </div>
                    <div class="file-stats">
                        <div class="mb-1">
                            <small class="text-muted me-2">Original:</small>
                            <span class="badge bg-secondary me-1">${file.distance} km</span>
                            <span class="badge bg-secondary me-1">${file.ascent} m</span>
                            ${originalDurationBadge}
                        </div>
                        <div>
                            <small class="text-muted me-2">Scaled:</small>
                            <span class="badge bg-primary me-1">${scaledDistance.toFixed(1)} km</span>
                            <span class="badge bg-success me-1">${scaledAscent.toFixed(0)} m</span>
                            ${scaledDurationBadge}
                        </div>
                    </div>
                `;
                const removeBtn = fileElement.querySelector('.remove-file-btn');
                removeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.uploadedFiles.delete(fileId);
                    if (this.selectedFileId === fileId) {
                        const nextId = Array.from(this.uploadedFiles.keys())[0];
                        this.selectedFileId = nextId || null;
                    }
                    this.updateUploadedFilesList();
                    this.updateProcessButton();
                });
                fileElement.addEventListener('click', () => this.selectFile(fileId));
                container.appendChild(fileElement);
            }
            container.scrollTop = prevScroll;
        } finally {
            this._updatingFilesList = false;
        }
    }

    async selectFile(fileId) {
        this.selectedFileId = fileId;
        this.updateUploadedFilesList();

        try {
            console.log('Selecting file:', fileId);

            // Get original route data
            const response = await fetch(`/preview/${fileId}`);
            const result = await response.json();
            console.log('Preview response:', result);

            if (result.success) {
                // Update charts and statistics with original data
                this.updateElevationChart(result.route_data);

                // Always calculate original and scaled timing if timing is enabled
                let timingData = result.timing || {};
                const addTiming = document.getElementById('addTiming').checked;
                if (addTiming) {
                    const power = parseFloat(document.getElementById('powerWatts')?.value) || 200;
                    const weight = parseFloat(document.getElementById('weightKg')?.value) || 75;
                    const g = 9.81;
                    const Cr = 0.005;
                    const CdA = 0.3;
                    const rho = 1.225;
                    const wind = 0;
                    // Original
                    const originalDistance = result.route_data.total_distance;
                    const originalAscent = result.route_data.total_ascent;
                    const flatDistanceOrig = originalDistance - (originalAscent / 1000);
                    const ascentDistanceOrig = originalAscent / 1000;
                    function estimateSpeed(power, weight, gradient) {
                        let v = 8;
                        for (let i = 0; i < 10; i++) {
                            const rolling = Cr * weight * g * v;
                            const air = 0.5 * CdA * rho * Math.pow(v + wind, 3);
                            const gravity = weight * g * gradient * v;
                            const f = rolling + air + gravity - power;
                            const df = Cr * weight * g + 1.5 * CdA * rho * Math.pow(v + wind, 2) + weight * g * gradient;
                            v = v - f / df;
                            if (v < 1) v = 1;
                        }
                        return v;
                    }
                    const ascentGradientOrig = originalAscent / (ascentDistanceOrig * 1000);
                    const ascentSpeedOrig = estimateSpeed(power, weight, ascentGradientOrig);
                    const ascentTimeOrig = ascentDistanceOrig * 1000 / ascentSpeedOrig;
                    const flatSpeedOrig = estimateSpeed(power, weight, 0);
                    const flatTimeOrig = flatDistanceOrig * 1000 / flatSpeedOrig;
                    timingData.original_duration_hours = (ascentTimeOrig + flatTimeOrig) / 3600;

                    // Scaled (if available)
                    if (result.scaled) {
                        const scaledDistance = result.scaled.total_distance;
                        const scaledAscent = result.scaled.total_ascent;
                        const flatDistanceScaled = scaledDistance - (scaledAscent / 1000);
                        const ascentDistanceScaled = scaledAscent / 1000;
                        const ascentGradientScaled = scaledAscent / (ascentDistanceScaled * 1000);
                        const ascentSpeedScaled = estimateSpeed(power, weight, ascentGradientScaled);
                        const ascentTimeScaled = ascentDistanceScaled * 1000 / ascentSpeedScaled;
                        const flatSpeedScaled = estimateSpeed(power, weight, 0);
                        const flatTimeScaled = flatDistanceScaled * 1000 / flatSpeedScaled;
                        timingData.scaled_duration_hours = (ascentTimeScaled + flatTimeScaled) / 3600;
                    }
                }
                this.updateStatistics(result.route_data, result.scaled || null, timingData);

                // Now also get the scaled version immediately
                await this.updatePreview();
            }
        } catch (error) {
            console.error('Failed to load preview:', error);
            this.showError('Failed to load preview: ' + error.message);
        }
    }

    updateScaleValues() {
        const distanceScale = parseFloat(document.getElementById('distanceScale').value);
        const ascentScale = parseFloat(document.getElementById('ascentScale').value);

        document.getElementById('distanceScaleValue').textContent = distanceScale.toFixed(3);
        document.getElementById('ascentScaleValue').textContent = ascentScale.toFixed(3);

        // Update file cards with new scaled values
        this.updateUploadedFilesList();

        // Update preview with new scale values
        this.updatePreview();
    }

    async updatePreview() {
        if (!this.selectedFileId) return;

        const distanceScale = document.getElementById('distanceScale').value;
        const ascentScale = document.getElementById('ascentScale').value;
        const startLat = document.getElementById('startLat').value;
        const startLon = document.getElementById('startLon').value;

        // Build URL with timing parameters if enabled
        let url = `/preview_scaled/${this.selectedFileId}?distance_scale=${distanceScale}&ascent_scale=${ascentScale}&start_lat=${startLat}&start_lon=${startLon}`;

        const addTiming = document.getElementById('addTiming').checked;
        if (addTiming) {
            const powerWatts = document.getElementById('powerWatts').value;
            const weightKg = document.getElementById('weightKg').value;
            url += `&power_watts=${powerWatts}&weight_kg=${weightKg}`;
        }

        try {
            const response = await fetch(url);
            const result = await response.json();

            if (result.success) {
                this.updateRoutePreview(result.original, result.scaled);
                this.updateElevationChart(result.original, result.scaled);

                // Always calculate original and scaled timing if timing is enabled
                let timingData = result.timing || {};
                if (addTiming) {
                    const power = parseFloat(document.getElementById('powerWatts')?.value) || 200;
                    const weight = parseFloat(document.getElementById('weightKg')?.value) || 75;
                    const g = 9.81;
                    const Cr = 0.005;
                    const CdA = 0.3;
                    const rho = 1.225;
                    const wind = 0;
                    // Original
                    const originalDistance = result.original.total_distance;
                    const originalAscent = result.original.total_ascent;
                    const flatDistanceOrig = originalDistance - (originalAscent / 1000);
                    const ascentDistanceOrig = originalAscent / 1000;
                    function estimateSpeed(power, weight, gradient) {
                        let v = 8;
                        for (let i = 0; i < 10; i++) {
                            const rolling = Cr * weight * g * v;
                            const air = 0.5 * CdA * rho * Math.pow(v + wind, 3);
                            const gravity = weight * g * gradient * v;
                            const f = rolling + air + gravity - power;
                            const df = Cr * weight * g + 1.5 * CdA * rho * Math.pow(v + wind, 2) + weight * g * gradient;
                            v = v - f / df;
                            if (v < 1) v = 1;
                        }
                        return v;
                    }
                    const ascentGradientOrig = originalAscent / (ascentDistanceOrig * 1000);
                    const ascentSpeedOrig = estimateSpeed(power, weight, ascentGradientOrig);
                    const ascentTimeOrig = ascentDistanceOrig * 1000 / ascentSpeedOrig;
                    const flatSpeedOrig = estimateSpeed(power, weight, 0);
                    const flatTimeOrig = flatDistanceOrig * 1000 / flatSpeedOrig;
                    timingData.original_duration_hours = (ascentTimeOrig + flatTimeOrig) / 3600;

                    // Scaled
                    if (result.scaled) {
                        const scaledDistance = result.scaled.total_distance;
                        const scaledAscent = result.scaled.total_ascent;
                        const flatDistanceScaled = scaledDistance - (scaledAscent / 1000);
                        const ascentDistanceScaled = scaledAscent / 1000;
                        const ascentGradientScaled = scaledAscent / (ascentDistanceScaled * 1000);
                        const ascentSpeedScaled = estimateSpeed(power, weight, ascentGradientScaled);
                        const ascentTimeScaled = ascentDistanceScaled * 1000 / ascentSpeedScaled;
                        const flatSpeedScaled = estimateSpeed(power, weight, 0);
                        const flatTimeScaled = flatDistanceScaled * 1000 / flatSpeedScaled;
                        timingData.scaled_duration_hours = (ascentTimeScaled + flatTimeScaled) / 3600;
                    }
                }
                this.updateStatistics(result.original, result.scaled, timingData);
            }
        } catch (error) {
            console.error('Preview update failed:', error);
        }
    }

    updateRoutePreview(originalData, scaledData = null) {
        console.log('updateRoutePreview called with:', { originalData, scaledData });

        // Clear previous route layers
        if (this.originalLayer) {
            this.originalLayer.clearLayers();
        }
        if (this.scaledLayer) {
            this.scaledLayer.clearLayers();
        }

        if (!originalData || !originalData.points || originalData.points.length === 0) {
            console.log('No original data available');
            return;
        }

        try {
            console.log('Updating route preview with data:', { originalData, scaledData });

            // Update original route on map
            this.updateRouteOnMap(this.originalMap, this.originalLayer, originalData.points, '#6c757d');

            // Update scaled route on map if available
            if (scaledData && scaledData.points) {
                this.updateRouteOnMap(this.scaledMap, this.scaledLayer, scaledData.points, '#0d6efd');
            }

        } catch (error) {
            console.error('Error updating route preview:', error);
            this.showError('Failed to display route preview: ' + error.message);
        }
    }

    updateRouteOnMap(map, layer, points, color) {
        if (!map || !layer || !points || points.length < 2) {
            return;
        }

        // Convert points to Leaflet LatLng format
        const latLngs = points.map(point => [point.lat, point.lon]);

        // Create polyline for the route
        const polyline = L.polyline(latLngs, {
            color: color,
            weight: 3,
            opacity: 0.8
        });

        // Add polyline to layer
        layer.addLayer(polyline);

        // Add start marker (green)
        const startMarker = L.circleMarker([points[0].lat, points[0].lon], {
            radius: 6,
            fillColor: '#28a745',
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        });
        layer.addLayer(startMarker);

        // Add end marker (red)
        if (points.length > 1) {
            const endPoint = points[points.length - 1];
            const endMarker = L.circleMarker([endPoint.lat, endPoint.lon], {
                radius: 6,
                fillColor: '#dc3545',
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            });
            layer.addLayer(endMarker);
        }

        // Fit map to route bounds with padding
        const bounds = L.latLngBounds(latLngs);
        map.fitBounds(bounds, { padding: [20, 20] });
    }

    updateElevationChart(originalData, scaledData = null) {
        // Update original elevation chart
        if (this.originalElevationChart) {
            if (!originalData || !originalData.distances || !originalData.elevations) {
                this.originalElevationChart.data.labels = [];
                this.originalElevationChart.data.datasets[0].data = [];
                this.originalElevationChart.update();
            } else {
                this.originalElevationChart.data.labels = originalData.distances.map(d => d.toFixed(1));
                this.originalElevationChart.data.datasets[0].data = originalData.elevations;
                this.originalElevationChart.update();
            }
        }

        // Update scaled elevation chart
        if (this.scaledElevationChart) {
            if (!scaledData || !scaledData.distances || !scaledData.elevations) {
                this.scaledElevationChart.data.labels = [];
                this.scaledElevationChart.data.datasets[0].data = [];
                this.scaledElevationChart.update();
            } else {
                this.scaledElevationChart.data.labels = scaledData.distances.map(d => d.toFixed(1));
                this.scaledElevationChart.data.datasets[0].data = scaledData.elevations;
                this.scaledElevationChart.update();
            }
        }
    }

    updateStatistics(originalData, scaledData = null, timingData = null) {
        const container = document.getElementById('statisticsDisplay');

        if (!originalData) {
            container.innerHTML = '<p class="text-muted">No data available</p>';
            return;
        }

        let html = `
            <table class="table table-sm statistics-table">
                <tr>
                    <td><strong>Original Distance:</strong></td>
                    <td>${originalData.total_distance.toFixed(1)} km</td>
                </tr>
                <tr>
                    <td><strong>Original Ascent:</strong></td>
                    <td>${originalData.total_ascent.toFixed(0)} m</td>
                </tr>
        `;

        // Add original timing if available
        if (timingData && timingData.original_duration_hours) {
            const originalHours = Math.floor(timingData.original_duration_hours);
            const originalMinutes = Math.round((timingData.original_duration_hours - originalHours) * 60);
            html += `
                <tr>
                    <td><strong>Original Duration:</strong></td>
                    <td>${originalHours}h ${originalMinutes}m</td>
                </tr>
            `;
        }

        if (scaledData) {
            html += `
                <tr class="comparison-row">
                    <td><strong>Scaled Distance:</strong></td>
                    <td>${scaledData.total_distance.toFixed(1)} km</td>
                </tr>
                <tr>
                    <td><strong>Scaled Ascent:</strong></td>
                    <td>${scaledData.total_ascent.toFixed(0)} m</td>
                </tr>
            `;

            // Add scaled timing if available
            if (timingData && timingData.scaled_duration_hours) {
                const scaledHours = Math.floor(timingData.scaled_duration_hours);
                const scaledMinutes = Math.round((timingData.scaled_duration_hours - scaledHours) * 60);
                html += `
                    <tr>
                        <td><strong>Scaled Duration:</strong></td>
                        <td>${scaledHours}h ${scaledMinutes}m</td>
                    </tr>
                `;
            }

            html += `
                <tr>
                    <td><strong>Distance Change:</strong></td>
                    <td class="${scaledData.total_distance > originalData.total_distance ? 'text-success' : 'text-danger'}">
                        ${((scaledData.total_distance / originalData.total_distance - 1) * 100).toFixed(1)}%
                    </td>
                </tr>
                <tr>
                    <td><strong>Ascent Change:</strong></td>
                    <td class="${scaledData.total_ascent > originalData.total_ascent ? 'text-success' : 'text-danger'}">
                        ${((scaledData.total_ascent / originalData.total_ascent - 1) * 100).toFixed(1)}%
                    </td>
                </tr>
            `;

            // Add timing change if available
            if (timingData && timingData.original_duration_hours && timingData.scaled_duration_hours) {
                const timingChangePercent = ((timingData.scaled_duration_hours / timingData.original_duration_hours - 1) * 100);
                html += `
                    <tr>
                        <td><strong>Duration Change:</strong></td>
                        <td class="${timingData.scaled_duration_hours > timingData.original_duration_hours ? 'text-danger' : 'text-success'}">
                            ${timingChangePercent.toFixed(1)}%
                        </td>
                    </tr>
                `;
            }
        }

        html += '</table>';
        container.innerHTML = html;
    }

    toggleTimingControls() {
        const checkbox = document.getElementById('addTiming');
        const controls = document.getElementById('timingControls');
        controls.style.display = checkbox.checked ? 'block' : 'none';

        // Update file cards to show/hide duration badges
        this.updateUploadedFilesList();
    }

    updateProcessButton() {
        const button = document.getElementById('processAllBtn');
        const disabled = this.uploadedFiles.size === 0;
        console.log('updateProcessButton called, files:', this.uploadedFiles.size, 'disabled:', disabled);
        button.disabled = disabled;
    }

    async processAllFiles() {

        console.log('processAllFiles called, uploaded files count:', this.uploadedFiles.size);

        if (this.uploadedFiles.size === 0) {
            console.log('No files to process, returning');
            return;
        }

        console.log('Starting file processing...');
        const fileIds = Array.from(this.uploadedFiles.keys());
        const distanceScale = parseFloat(document.getElementById('distanceScale').value);
        const ascentScale = parseFloat(document.getElementById('ascentScale').value);
        const startLat = parseFloat(document.getElementById('startLat').value);
        const startLon = parseFloat(document.getElementById('startLon').value);
        const baseName = document.getElementById('baseName').value.trim();
        const outputFormat = document.getElementById('outputFormat').value;
        const addTiming = document.getElementById('addTiming').checked;
        const powerWatts = addTiming ? parseInt(document.getElementById('powerWatts').value) : null;
        const weightKg = addTiming ? parseInt(document.getElementById('weightKg').value) : null;

        // TRACE: Log the scale values being sent
        console.log('[TRACE] processAllFiles: distanceScale =', distanceScale, ', ascentScale =', ascentScale);

        const requestData = {
            file_ids: fileIds,
            distance_scale: distanceScale,
            ascent_scale: ascentScale,
            start_lat: startLat,
            start_lon: startLon,
            base_name: baseName,
            output_format: outputFormat,
            add_timing: addTiming,
            power_watts: powerWatts,
            weight_kg: weightKg
        };

        console.log('[TRACE] processAllFiles: requestData =', requestData);

        try {
            this.showProcessingProgress(true);
            this.initializeFileProgressBars(fileIds);

            const response = await fetch('/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();
            console.log('Process response:', result);

            if (result.success && result.session_id) {
                console.log('Starting progress tracking for session:', result.session_id);
                // Start listening for progress updates
                this.trackProgress(result.session_id);
            } else {
                console.error('Processing failed:', result.error);
                this.showError(result.error || 'Failed to start processing');
                this.showProcessingProgress(false);
            }
        } catch (error) {
            console.error('Processing error:', error);
            this.showError('Processing failed: ' + error.message);
            this.showProcessingProgress(false);
        }
    }

    updateProcessedFilesList() {
        const container = document.getElementById('processedFiles');
        container.innerHTML = '';

        if (this.processedFiles.size === 0) {
            return;
        }

        // Add batch download button
        const batchDownloadBtn = document.createElement('button');
        batchDownloadBtn.className = 'btn btn-primary btn-sm w-100 mb-2';
        batchDownloadBtn.innerHTML = '<i class="fas fa-download me-2"></i>Download All as ZIP';
        batchDownloadBtn.addEventListener('click', this.downloadBatch.bind(this));
        container.appendChild(batchDownloadBtn);

        // Add individual files
        this.processedFiles.forEach((file, fileId) => {
            const fileElement = document.createElement('div');
            fileElement.className = 'processed-file-item';
            fileElement.innerHTML = `
                <div>
                    <div class="fw-bold">${file.filename}</div>
                    <small class="text-muted">${file.original_filename}</small>
                    <span class="badge bg-primary format-badge ms-2">${file.format}</span>
                </div>
                <button class="btn btn-sm btn-outline-primary" onclick="app.downloadFile('${fileId}')">
                    <i class="fas fa-download"></i>
                </button>
            `;
            container.appendChild(fileElement);
        });
    }

    async downloadFile(fileId) {
        try {
            const response = await fetch(`/download/${fileId}`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = this.processedFiles.get(fileId).filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                this.showError('Download failed');
            }
        } catch (error) {
            this.showError('Download failed: ' + error.message);
        }
    }

    async downloadBatch() {
        const fileIds = Array.from(this.processedFiles.keys());

        try {
            const response = await fetch('/download_batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ processed_ids: fileIds })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'scaled_gpx_files.zip';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                this.showError('Batch download failed');
            }
        } catch (error) {
            this.showError('Batch download failed: ' + error.message);
        }
    }

    showLoading(show) {
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        if (show) {
            modal.show();
        } else {
            modal.hide();
        }
    }

    showProcessingProgress(show) {
        const progress = document.getElementById('processingProgress');
        const button = document.getElementById('processAllBtn');

        if (show) {
            progress.style.display = 'block';
            button.disabled = true;
        } else {
            progress.style.display = 'none';
            button.disabled = false;
        }
    }

    showUploadProgress(show) {
        const progress = document.getElementById('uploadProgress');
        if (show) {
            progress.style.display = 'block';
        } else {
            progress.style.display = 'none';
        }
    }

    initializeUploadProgressBars(files) {
        const container = document.getElementById('uploadProgressItems');
        container.innerHTML = '';

        files.forEach((file, index) => {
            const progressItem = document.createElement('div');
            progressItem.className = 'mb-2';
            progressItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <small class="text-muted">${file.name}</small>
                    <small id="uploadStatus-${index}" class="text-info">Preparing...</small>
                </div>
                <div class="progress" style="height: 4px;">
                    <div id="uploadBar-${index}" class="progress-bar bg-info"
                         role="progressbar" style="width: 0%"></div>
                </div>
            `;
            container.appendChild(progressItem);
        });
    }

    updateUploadFileProgress(index, percent, status, statusText) {
        const statusElement = document.getElementById(`uploadStatus-${index}`);
        const barElement = document.getElementById(`uploadBar-${index}`);

        if (statusElement && barElement) {
            statusElement.textContent = statusText;
            barElement.style.width = `${percent}%`;

            // Update colors based on status
            statusElement.className = `text-${status}`;
            barElement.className = `progress-bar bg-${status}`;
        }
    }

    initializeFileProgressBars(fileIds) {
        const container = document.getElementById('fileProgressList');
        container.innerHTML = '';

        fileIds.forEach(fileId => {
            if (this.uploadedFiles.has(fileId)) {
                const file = this.uploadedFiles.get(fileId);
                const progressItem = document.createElement('div');
                progressItem.className = 'mb-2';
                progressItem.id = `progress-${fileId}`;
                progressItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <small class="fw-medium">${file.filename}</small>
                        <small class="text-muted" id="status-${fileId}">Waiting...</small>
                    </div>
                    <div class="progress" style="height: 6px;">
                        <div id="bar-${fileId}" class="progress-bar bg-info" role="progressbar" style="width: 0%"></div>
                    </div>
                `;
                container.appendChild(progressItem);
            }
        });
    }

    trackProgress(sessionId) {
        console.log('Starting progress tracking for session:', sessionId);
        const eventSource = new EventSource(`/progress/${sessionId}`);

        eventSource.onmessage = (event) => {
            console.log('Progress event received:', event.data);
            const data = JSON.parse(event.data);
            this.updateProgressDisplay(data);

            if (data.status === 'completed') {
                console.log('Processing completed');
                eventSource.close();
                this.handleProcessingComplete(data);
            } else if (data.status === 'failed') {
                console.log('Processing failed:', data.error);
                eventSource.close();
                this.showError(`Processing failed: ${data.error || 'Unknown error'}`);
                this.showProcessingProgress(false);
            }
        };

        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            eventSource.close();
            this.showError('Lost connection to progress updates');
            this.showProcessingProgress(false);
        };

        eventSource.onopen = () => {
            console.log('EventSource connection opened');
        };
    }

    updateProgressDisplay(data) {
        console.log('Updating progress display:', data);

        // Update overall progress
        const overallProgress = (data.current_file / data.total_files) * 100;
        const overallBar = document.getElementById('overallProgressBar');
        const overallText = document.getElementById('overallProgressText');

        if (overallBar && overallText) {
            overallBar.style.width = `${overallProgress}%`;
            overallText.textContent = `Processing ${data.current_file} of ${data.total_files} files...`;

            if (data.current_filename) {
                overallText.textContent += ` (${data.current_filename})`;
            }
            console.log('Updated overall progress:', overallProgress + '%');
        } else {
            console.error('Progress elements not found');
        }

        // Update individual file progress
        if (data.files) {
            Object.entries(data.files).forEach(([fileId, fileStatus]) => {
                const statusElement = document.getElementById(`status-${fileId}`);
                const barElement = document.getElementById(`bar-${fileId}`);

                if (statusElement && barElement) {
                    switch (fileStatus.status) {
                        case 'processing':
                            statusElement.textContent = 'Processing...';
                            statusElement.className = 'text-info';
                            barElement.className = 'progress-bar bg-info';
                            barElement.style.width = '50%';
                            break;
                        case 'completed':
                            statusElement.textContent = 'Completed';
                            statusElement.className = 'text-success';
                            barElement.className = 'progress-bar bg-success';
                            barElement.style.width = '100%';
                            break;
                        case 'failed':
                            statusElement.textContent = `Failed: ${fileStatus.error || 'Unknown error'}`;
                            statusElement.className = 'text-danger';
                            barElement.className = 'progress-bar bg-danger';
                            barElement.style.width = '100%';
                            break;
                    }
                }
            });
        }
    }

    handleProcessingComplete(data) {
        // Update final progress
        const overallBar = document.getElementById('overallProgressBar');
        const overallText = document.getElementById('overallProgressText');
        overallBar.style.width = '100%';
        overallBar.className = 'progress-bar bg-success';
        overallText.textContent = 'Processing completed!';

        // Add processed files to the list
        if (data.processed_files) {
            data.processed_files.forEach(file => {
                this.processedFiles.set(file.id, file);
            });
            this.updateProcessedFilesList();
            this.showSuccess(`${data.processed_files.length} file(s) processed successfully`);
        }

        // Hide progress after a delay
        setTimeout(() => {
            this.showProcessingProgress(false);
        }, 2000);
    }

    showError(message) {
        const alert = document.getElementById('errorAlert');
        const messageSpan = document.getElementById('errorMessage');
        messageSpan.textContent = message;
        alert.classList.add('show');
        alert.style.display = 'block';

        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.style.display = 'none', 150);
        }, 5000);
    }

    showSuccess(message) {
        const alert = document.getElementById('successAlert');
        const messageSpan = document.getElementById('successMessage');
        messageSpan.textContent = message;
        alert.classList.add('show');
        alert.style.display = 'block';

        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.style.display = 'none', 150);
        }, 3000);
    }
}

// Initialize the application when the page loads
let app;
document.addEventListener('DOMContentLoaded', function() {
    app = new GPXScalerApp();
});
