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

            // 1. Process Weather Data
            document.getElementById('weather-temp').textContent = `${data.weather.temp_f}°F`;
            document.getElementById('weather-condition').textContent = data.weather.condition;
            document.getElementById('weather-humidity').textContent = `${data.weather.humidity}%`;
            document.getElementById('weather-wind').textContent = `${data.weather.wind_speed} mph`;

            const weatherCard = document.querySelector('.weather-card');
            if (!data.hardware.weather_online) {
                weatherCard.style.opacity = "0.5";
                document.getElementById('weather-condition').textContent = "Weather Offline (Stale)";
            } else {
                weatherCard.style.opacity = "1.0";
            }

            const iconName = getIconFilename(data.weather.wmo_code, data.weather.is_day);
            document.getElementById('weather-icon-container').innerHTML = 
                `<object type="image/svg+xml" data="/static/weather-icons/${iconName}" class="weather-svg"></object>`;

            // 2. Process Forecast Data
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

            // 3. Process Epever Solar Data
            const s = data.solar;
            const statusBadge = document.getElementById('solar-status');
            statusBadge.textContent = s.status;
            statusBadge.className = `status-badge ${data.hardware.epever_online ? 'online' : 'offline'}`;
            
            document.getElementById('solar-state').textContent = s.state;
            document.getElementById('solar-w-pv').textContent = s.w_pv;
            document.getElementById('solar-v-pv').textContent = s.v_pv;
            document.getElementById('solar-a-pv').textContent = s.a_pv;
            document.getElementById('solar-w-bat').textContent = s.w_bat;
            document.getElementById('solar-v-bat').textContent = s.v_bat;
            document.getElementById('solar-a-bat').textContent = s.a_bat;
            document.getElementById('solar-temp-dev').textContent = `${s.device_t}°C`;
            document.getElementById('solar-temp-bat').textContent = `${s.battery_t}°C`;
            document.getElementById('solar-kwh').textContent = `${s.total_kwh} kWh`;

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
