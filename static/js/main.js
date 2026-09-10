let isUiOnline = true;
let telemetryFailCount = 0;

function updateClock() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
    });
    document.getElementById('current-date').textContent = now.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
}

function getIconFilename(wmoCode, isDay = 1) {
    if (wmoCode === 0) return isDay ? 'clear-day.svg' : 'clear-night.svg';
    if (wmoCode >= 1 && wmoCode <= 3) return isDay ? 'partly-cloudy-day.svg' : 'partly-cloudy-night.svg';
    if (wmoCode >= 45 && wmoCode <= 48) return 'fog.svg';
    if ((wmoCode >= 51 && wmoCode <= 67) || (wmoCode >= 80 && wmoCode <= 82)) return 'rain.svg';
    if ((wmoCode >= 71 && wmoCode <= 77) || (wmoCode >= 85 && wmoCode <= 86)) return 'snow.svg';
    if (wmoCode >= 95) return 'thunderstorms.svg';
    return 'not-available.svg';
}

function parseForecastDate(dateStr) {
    const parts = dateStr.split('-');
    const dateObj = new Date(parts[0], parts[1] - 1, parts[2]);
    return dateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

function fetchTelemetrySmart() {
    fetch('/api/data')
        .then(response => {
            if (!response.ok) throw new Error("Network drop");
            return response.json();
        })
        .then(data => {
            telemetryFailCount = 0;
            if (!isUiOnline) {
                isUiOnline = true;
                document.body.style.opacity = "1.0";
            }

            // 1. Render Weather Components
            document.getElementById('weather-temp').textContent = `${data.weather.temp_f}°F`;
            document.getElementById('weather-condition').textContent = data.weather.condition;
            document.getElementById('weather-humidity').textContent = `${data.weather.humidity}%`;
            document.getElementById('weather-wind').textContent = `${data.weather.wind_speed} mph`;

            const iconName = getIconFilename(data.weather.wmo_code, data.weather.is_day);
            document.getElementById('weather-icon-container').innerHTML = 
                `<object type="image/svg+xml" data="/static/weather-icons/${iconName}" class="weather-svg"></object>`;

            // 2. Render Forecast Array Rows
            const forecastContainer = document.getElementById('forecast-grid-container');
            forecastContainer.innerHTML = '';
            data.forecast.forEach((day, index) => {
                const dateLabel = index === 0 ? "Today" : parseForecastDate(day.date_raw);
                const forecastIcon = getIconFilename(day.wmo_code, 1);
                const dayHtml = `
                    <div class="forecast-day-item">
                        <div class="forecast-date">${dateLabel}</div>
                        <div class="forecast-icon-box"><object type="image/svg+xml" data="/static/weather-icons/${forecastIcon}" class="forecast-svg"></object></div>
                        <div class="forecast-temps"><span class="high">${day.max_temp}°</span><span class="low">${day.min_temp}°</span></div>
                    </div>`;
                forecastContainer.insertAdjacentHTML('beforeend', dayHtml);
            });

            // 3. Render Epever Solar Fields
            const s = data.solar;
            const sBadge = document.getElementById('solar-status');
            sBadge.textContent = s.status;
            sBadge.className = `status-badge ${data.hardware.epever_online ? 'online' : 'offline'}`;
            
            document.getElementById('solar-state').textContent = s.state;
            document.getElementById('solar-w-pv').textContent = s.w_pv;
            document.getElementById('solar-v-pv').textContent = s.v_pv;
            document.getElementById('solar-a-pv').textContent = s.a_pv;
            document.getElementById('solar-w-bat').textContent = s.w_bat;
            document.getElementById('solar-v-bat').textContent = s.v_bat;
            document.getElementById('solar-a-bat').textContent = s.a_bat;
            document.getElementById('solar-temp-dev').textContent = `${s.device_t}°C`;
            document.getElementById('solar-kwh').textContent = `${s.total_kwh} kWh`;

            // 4. Render Lithium BMS & Animate Fluid Level Levels
            const b = data.bms;
            document.getElementById('bms-sys-state').textContent = b.status;
            document.getElementById('bms-v-avg').textContent = b.v_combined.toFixed(2);
            document.getElementById('bms-a-total').textContent = b.a_total.toFixed(2);
            document.getElementById('bms-w-total').textContent = Math.abs(b.w_total).toFixed(0);
            document.getElementById('bms-ah-total').textContent = b.ah_total.toFixed(1);

            const fillPct = b.soc_avg;
            const fluidBar = document.getElementById('battery-fluid-level');
            fluidBar.style.width = `${fillPct}%`;
            document.getElementById('battery-percentage-text').textContent = `${fillPct}%`;

            if (fillPct <= 20) fluidBar.style.backgroundColor = "#ff1744"; // Warning Red
            else if (fillPct <= 50) fluidBar.style.backgroundColor = "#ff9100"; // Warning Shift Orange
            else fluidBar.style.backgroundColor = "#00e676"; // Lithium Green

            // Map sub-pack cell indicators
            document.getElementById('b1-status').textContent = b.b1_status;
            document.getElementById('b1-soc').textContent = b.b1_soc;
            document.getElementById('b1-v').textContent = b.b1_v.toFixed(1);
            document.getElementById('b1-a').textContent = b.b1_a.toFixed(1);

            document.getElementById('b2-status').textContent = b.b2_status;
            document.getElementById('b2-soc').textContent = b.b2_soc;
            document.getElementById('b2-v').textContent = b.b2_v.toFixed(1);
            document.getElementById('b2-a').textContent = b.b2_a.toFixed(1);

            setTimeout(fetchTelemetrySmart, 3000);
        })
        .catch(error => {
            isUiOnline = false;
            telemetryFailCount++;
            document.body.style.opacity = "0.4";
            const nextRetryDelay = Math.min(3000 * Math.pow(2, telemetryFailCount - 1), 30000);
            setTimeout(fetchTelemetrySmart, nextRetryDelay);
        });
}

setInterval(updateClock, 1000);
updateClock();
fetchTelemetrySmart();
