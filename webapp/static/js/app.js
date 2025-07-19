// GPX Scaler Web App JavaScript

class GPXScalerApp {
    constructor() {
        this.uploadedFiles = new Map();
        this.selectedFileId = null;
        this.processedFiles = new Map();
        this.originalElevationChart = null;
        this.scaledElevationChart = null;

        this.loadSavedParameters();
        this.initializeEventListeners();
        this.initializeCharts();
    }

    loadSavedParameters() {
        try {
            // Load saved parameters from localStorage
            const savedParams = localStorage.getItem('gpxScalerParams');
            if (savedParams) {
                const params = JSON.parse(savedParams);

                // Set form values if elements exist
                if (params.distanceScale && document.getElementById('distanceScale')) {
                    document.getElementById('distanceScale').value = params.distanceScale;
                    document.getElementById('distanceScaleValue').textContent = parseFloat(params.distanceScale).toFixed(3);
                }
                if (params.ascentScale && document.getElementById('ascentScale')) {
                    document.getElementById('ascentScale').value = params.ascentScale;
                    document.getElementById('ascentScaleValue').textContent = parseFloat(params.ascentScale).toFixed(3);
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
        // File upload events
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');

        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', this.handleDragOver.bind(this));
        dropZone.addEventListener('drop', this.handleDrop.bind(this));
        dropZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));

        // Slider events
        document.getElementById('distanceScale').addEventListener('input', () => {
            this.updateScaleValues();
            this.saveParameters();
        });
        document.getElementById('ascentScale').addEventListener('input', () => {
            this.updateScaleValues();
            this.saveParameters();
        });
        document.getElementById('startLat').addEventListener('input', () => {
            this.updatePreview();
            this.saveParameters();
        });
        document.getElementById('startLon').addEventListener('input', () => {
            this.updatePreview();
            this.saveParameters();
        });

        // Timing controls
        document.getElementById('addTiming').addEventListener('change', (e) => {
            this.toggleTimingControls();
            this.updatePreview(); // Update preview when timing is toggled
            this.saveParameters();
        });

        // Add listeners for timing inputs (when they exist)
        const powerInput = document.getElementById('powerWatts');
        const weightInput = document.getElementById('weightKg');
        if (powerInput) {
            powerInput.addEventListener('input', () => {
                this.updateUploadedFilesList(); // Update file cards with new duration
                this.updatePreview(); // Update preview
                this.saveParameters();
            });
        }
        if (weightInput) {
            weightInput.addEventListener('input', () => {
                this.updateUploadedFilesList(); // Update file cards with new duration
                this.updatePreview(); // Update preview
                this.saveParameters();
            });
        }

        // Add event listeners for other form controls
        const baseNameInput = document.getElementById('baseName');
        const outputFormatSelect = document.getElementById('outputFormat');

        if (baseNameInput) {
            baseNameInput.addEventListener('input', () => {
                this.saveParameters();
            });
        }

        if (outputFormatSelect) {
            outputFormatSelect.addEventListener('change', () => {
                this.saveParameters();
            });
        }

        // Process button
        document.getElementById('processAllBtn').addEventListener('click', (e) => {
            console.log('Process All Files button clicked!');
            this.processAllFiles.bind(this)(e);
        });
    }

    initializeCharts() {
        // Original elevation chart
        const originalCtx = document.getElementById('originalElevationChart').getContext('2d');
        this.originalElevationChart = new Chart(originalCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Original Elevation',
                    data: [],
                    borderColor: '#6c757d',
                    backgroundColor: 'rgba(108, 117, 125, 0.1)',
                    tension: 0.2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Elevation (m)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });

        // Scaled elevation chart
        const scaledCtx = document.getElementById('scaledElevationChart').getContext('2d');
        this.scaledElevationChart = new Chart(scaledCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Scaled Elevation',
                    data: [],
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    tension: 0.2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Elevation (m)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.currentTarget.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');

        const files = Array.from(e.dataTransfer.files).filter(file =>
            file.name.toLowerCase().endsWith('.gpx')
        );

        if (files.length > 0) {
            this.uploadFiles(files);
        } else {
            this.showError('Please drop only GPX files');
        }
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.uploadFiles(files);
        e.target.value = ''; // Reset input
    }

    async uploadFiles(files) {
        try {
            this.showUploadProgress(true);
            this.initializeUploadProgressBars(files);

            const uploadedFiles = [];

            // Upload files one by one to show individual progress
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                console.log(`Uploading file ${i + 1}/${files.length}: ${file.name}`);

                try {
                    const result = await this.uploadSingleFile(file, i);
                    if (result.success && result.files.length > 0) {
                        uploadedFiles.push(...result.files);
                        this.updateUploadFileProgress(i, 100, 'success', 'Uploaded');
                    } else {
                        this.updateUploadFileProgress(i, 100, 'danger', 'Failed');
                        console.error(`Failed to upload ${file.name}:`, result.error);
                    }
                } catch (error) {
                    this.updateUploadFileProgress(i, 100, 'danger', 'Error');
                    console.error(`Error uploading ${file.name}:`, error);
                }
            }

            // Update the uploaded files list with all successfully uploaded files
            uploadedFiles.forEach(file => {
                this.uploadedFiles.set(file.id, file);
            });

            this.updateUploadedFilesList();
            this.updateProcessButton();

            if (uploadedFiles.length > 0) {
                this.showSuccess(`${uploadedFiles.length} file(s) uploaded successfully`);

                // Auto-select first file for preview
                if (!this.selectedFileId) {
                    this.selectFile(uploadedFiles[0].id);
                }
            }

            // Hide upload progress after a delay
            setTimeout(() => {
                this.showUploadProgress(false);
            }, 2000);

        } catch (error) {
            this.showError('Upload failed: ' + error.message);
            this.showUploadProgress(false);
        }
    }

    async uploadSingleFile(file, index) {
        const formData = new FormData();
        formData.append('files', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    this.updateUploadFileProgress(index, percentComplete, 'info', 'Uploading...');
                }
            };

            xhr.onload = () => {
                if (xhr.status === 200) {
                    try {
                        const result = JSON.parse(xhr.responseText);
                        resolve(result);
                    } catch (error) {
                        reject(new Error('Invalid response format'));
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            };

            xhr.onerror = () => {
                reject(new Error('Network error occurred'));
            };

            xhr.open('POST', '/upload');
            xhr.send(formData);
        });
    }

    calculateScaledValues(originalDistance, originalAscent) {
        const distanceScale = parseFloat(document.getElementById('distanceScale').value);
        const ascentScale = parseFloat(document.getElementById('ascentScale').value);

        const scaledDistance = originalDistance * distanceScale;
        const scaledAscent = originalAscent * ascentScale;

        // Calculate scaled duration using the same estimation approach as the backend
        const addTiming = document.getElementById('addTiming').checked;
        let scaledDuration = null;

        if (addTiming) {
            // Simple estimation: distance_factor * 0.8 + ascent_factor * 0.2
            const distanceFactor = distanceScale;
            const ascentFactor = ascentScale;
            const durationFactor = distanceFactor * 0.8 + ascentFactor * 0.2;

            // Estimate original duration (rough calculation: 1 hour per 20km + 1 hour per 1000m ascent)
            const estimatedOriginalDuration = (originalDistance / 20) + (originalAscent / 1000);
            scaledDuration = estimatedOriginalDuration * durationFactor;
        }

        return {
            distance: scaledDistance,
            ascent: scaledAscent,
            duration: scaledDuration
        };
    }

    updateUploadedFilesList() {
        const container = document.getElementById('uploadedFiles');
        container.innerHTML = '';

        this.uploadedFiles.forEach((file, fileId) => {
            const scaledValues = this.calculateScaledValues(file.distance, file.ascent);

            const fileElement = document.createElement('div');
            fileElement.className = `file-item ${fileId === this.selectedFileId ? 'selected' : ''}`;

            let durationBadge = '';
            if (scaledValues.duration) {
                const hours = Math.floor(scaledValues.duration);
                const minutes = Math.round((scaledValues.duration - hours) * 60);
                durationBadge = `<span class="badge bg-info me-1">${hours}h ${minutes}m</span>`;
            }

            fileElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <span class="fw-bold">${file.filename}</span>
                    <i class="fas fa-eye"></i>
                </div>
                <div class="file-stats">
                    <div class="mb-1">
                        <small class="text-muted me-2">Original:</small>
                        <span class="badge bg-secondary me-1">${file.distance} km</span>
                        <span class="badge bg-secondary me-1">${file.ascent} m</span>
                    </div>
                    <div>
                        <small class="text-muted me-2">Scaled:</small>
                        <span class="badge bg-primary me-1">${scaledValues.distance.toFixed(1)} km</span>
                        <span class="badge bg-success me-1">${scaledValues.ascent.toFixed(0)} m</span>
                        ${durationBadge}
                    </div>
                </div>
            `;

            fileElement.addEventListener('click', () => this.selectFile(fileId));
            container.appendChild(fileElement);
        });
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
                this.updateStatistics(result.route_data);

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
                this.updateStatistics(result.original, result.scaled, result.timing);
            }
        } catch (error) {
            console.error('Preview update failed:', error);
        }
    }

    updateRoutePreview(originalData, scaledData = null) {
        console.log('updateRoutePreview called with:', { originalData, scaledData });
        const originalCanvas = document.getElementById('originalRouteCanvas');
        const scaledCanvas = document.getElementById('scaledRouteCanvas');

        console.log('Canvas elements found:', { originalCanvas, scaledCanvas });

        // Clear previous content
        originalCanvas.innerHTML = '';
        scaledCanvas.innerHTML = '';

        if (!originalData || !originalData.points || originalData.points.length === 0) {
            console.log('No original data available');
            originalCanvas.innerHTML = '<p class="text-muted text-center">No route data available</p>';
            scaledCanvas.innerHTML = '<p class="text-muted text-center">Adjust sliders to see scaled route</p>';
            return;
        }

        try {
            console.log('Updating route preview with data:', { originalData, scaledData });

            // Create and update original route SVG
            this.updateSingleRouteCanvasWithData(originalCanvas, originalData.points, 'route-original');

            // Create and update scaled route SVG if available
            if (scaledData && scaledData.points) {
                this.updateSingleRouteCanvasWithData(scaledCanvas, scaledData.points, 'route-scaled');
            } else {
                scaledCanvas.innerHTML = '<p class="text-muted text-center">Adjust sliders to see scaled route</p>';
            }

        } catch (error) {
            console.error('Error updating route preview:', error);
            originalCanvas.innerHTML = `<p class="text-danger text-center">Error displaying route: ${error.message}</p>`;
            scaledCanvas.innerHTML = `<p class="text-danger text-center">Error displaying route: ${error.message}</p>`;
            this.showError('Failed to display route preview: ' + error.message);
        }
    }

    updateSingleRouteCanvas(canvas, points, bounds, scale, routeClass) {
        // Create SVG
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'route-svg');
        svg.setAttribute('viewBox', '0 0 300 300');

        // Calculate proper centering offset
        const { offsetX, offsetY } = this.calculateOffset(bounds, scale, 300, 300);

        // Draw route with centered positioning
        this.drawRoute(svg, points, bounds, scale, routeClass, offsetX, offsetY);

        // Add start/end markers with centered positioning
        this.addRouteMarkers(svg, points, bounds, scale, offsetX, offsetY);

        canvas.appendChild(svg);
    }

    updateSingleRouteCanvasWithData(canvas, points, routeClass) {
        if (!points || points.length < 2) {
            canvas.innerHTML = '<p class="text-muted text-center">No route data available</p>';
            return;
        }

        // Calculate bounds for this specific route
        const bounds = this.calculateSingleRouteBounds(points);
        console.log('Calculated bounds for', routeClass, ':', bounds);

        if (!this.isValidBounds(bounds)) {
            throw new Error('Invalid route bounds calculated for ' + routeClass);
        }

        const scale = this.calculateScale(bounds, 300, 300);
        console.log('Calculated scale for', routeClass, ':', scale);

        if (!isFinite(scale) || scale <= 0) {
            throw new Error('Invalid scale calculated for ' + routeClass);
        }

        // Create SVG
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'route-svg');
        svg.setAttribute('viewBox', '0 0 300 300');

        // Calculate proper centering offset
        const { offsetX, offsetY } = this.calculateOffset(bounds, scale, 300, 300);

        // Draw route with centered positioning
        this.drawRoute(svg, points, bounds, scale, routeClass, offsetX, offsetY);

        // Add start/end markers with centered positioning
        this.addRouteMarkers(svg, points, bounds, scale, offsetX, offsetY);

        canvas.appendChild(svg);
    }

    calculateSingleRouteBounds(points) {
        const lats = points.map(p => p.lat).filter(lat => isFinite(lat));
        const lons = points.map(p => p.lon).filter(lon => isFinite(lon));

        if (lats.length === 0 || lons.length === 0) {
            throw new Error('No valid coordinate data found');
        }

        return {
            minLat: Math.min(...lats),
            maxLat: Math.max(...lats),
            minLon: Math.min(...lons),
            maxLon: Math.max(...lons)
        };
    }

    calculateViewBounds(originalData, scaledData = null) {
        const allPoints = [...originalData.points];
        if (scaledData && scaledData.points) {
            allPoints.push(...scaledData.points);
        }

        const lats = allPoints.map(p => p.lat).filter(lat => isFinite(lat));
        const lons = allPoints.map(p => p.lon).filter(lon => isFinite(lon));

        if (lats.length === 0 || lons.length === 0) {
            throw new Error('No valid coordinate data found');
        }

        return {
            minLat: Math.min(...lats),
            maxLat: Math.max(...lats),
            minLon: Math.min(...lons),
            maxLon: Math.max(...lons)
        };
    }

    isValidBounds(bounds) {
        return bounds &&
               isFinite(bounds.minLat) && isFinite(bounds.maxLat) &&
               isFinite(bounds.minLon) && isFinite(bounds.maxLon) &&
               bounds.maxLat > bounds.minLat &&
               bounds.maxLon > bounds.minLon;
    }

    calculateScale(bounds, width, height) {
        const latRange = bounds.maxLat - bounds.minLat;
        const lonRange = bounds.maxLon - bounds.minLon;

        // Add some padding (10% on each side)
        const padding = 0.1;
        const availableWidth = width * (1 - 2 * padding);
        const availableHeight = height * (1 - 2 * padding);

        const scaleX = availableWidth / lonRange;
        const scaleY = availableHeight / latRange;

        return Math.min(scaleX, scaleY);
    }

    calculateOffset(bounds, scale, viewWidth, viewHeight) {
        const latRange = bounds.maxLat - bounds.minLat;
        const lonRange = bounds.maxLon - bounds.minLon;

        // Calculate the size of the route in pixels
        const routeWidth = lonRange * scale;
        const routeHeight = latRange * scale;

        // Center the route in the viewport
        const offsetX = (viewWidth - routeWidth) / 2;
        const offsetY = (viewHeight - routeHeight) / 2;

        return { offsetX, offsetY };
    }

    drawRoute(svg, points, bounds, scale, className, offsetX, offsetY) {
        if (!points || points.length < 2) return;

        try {
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('class', `route-path ${className}`);

            let pathData = '';
            let validPointCount = 0;

            points.forEach((point, index) => {
                if (!point || !isFinite(point.lat) || !isFinite(point.lon)) {
                    console.warn(`Invalid point at index ${index}:`, point);
                    return;
                }

                const x = (point.lon - bounds.minLon) * scale + offsetX;
                const y = (bounds.maxLat - point.lat) * scale + offsetY; // Flip Y for north-up

                if (!isFinite(x) || !isFinite(y)) {
                    console.warn(`Invalid coordinates calculated for point ${index}: x=${x}, y=${y}`);
                    return;
                }

                if (validPointCount === 0) {
                    pathData += `M ${x} ${y}`;
                } else {
                    pathData += ` L ${x} ${y}`;
                }
                validPointCount++;
            });

            if (validPointCount < 2) {
                throw new Error(`Not enough valid points to draw route (${validPointCount})`);
            }

            path.setAttribute('d', pathData);
            svg.appendChild(path);

        } catch (error) {
            console.error('Error drawing route:', error);
            throw error;
        }
    }

    addRouteMarkers(svg, points, bounds, scale, offsetX, offsetY) {
        if (!points || points.length === 0) return;

        try {
            // Start marker (green)
            const startPoint = points[0];
            if (startPoint && isFinite(startPoint.lat) && isFinite(startPoint.lon)) {
                const startX = (startPoint.lon - bounds.minLon) * scale + offsetX;
                const startY = (bounds.maxLat - startPoint.lat) * scale + offsetY;

                if (isFinite(startX) && isFinite(startY)) {
                    const startMarker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                    startMarker.setAttribute('class', 'route-point route-start');
                    startMarker.setAttribute('cx', startX);
                    startMarker.setAttribute('cy', startY);
                    svg.appendChild(startMarker);
                }
            }

            // End marker (red)
            if (points.length > 1) {
                const endPoint = points[points.length - 1];
                if (endPoint && isFinite(endPoint.lat) && isFinite(endPoint.lon)) {
                    const endX = (endPoint.lon - bounds.minLon) * scale + offsetX;
                    const endY = (bounds.maxLat - endPoint.lat) * scale + offsetY;

                    if (isFinite(endX) && isFinite(endY)) {
                        const endMarker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                        endMarker.setAttribute('class', 'route-point route-end');
                        endMarker.setAttribute('cx', endX);
                        endMarker.setAttribute('cy', endY);
                        svg.appendChild(endMarker);
                    }
                }
            }
        } catch (error) {
            console.error('Error adding route markers:', error);
        }
    }

    updateElevationChart(originalData, scaledData = null) {
        // Update original elevation chart
        if (!originalData || !originalData.distances || !originalData.elevations) {
            this.originalElevationChart.data.labels = [];
            this.originalElevationChart.data.datasets[0].data = [];
            this.originalElevationChart.update();
        } else {
            this.originalElevationChart.data.labels = originalData.distances.map(d => d.toFixed(1));
            this.originalElevationChart.data.datasets[0].data = originalData.elevations;
            this.originalElevationChart.update();
        }

        // Update scaled elevation chart
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

        console.log('Request data:', requestData);

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
