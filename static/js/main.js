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
    // Corrects local time parsing offsets from standard YYYY-MM-DD frames
    const parts = dateStr.split('-');
    const dateObj = new Date(parts[0], parts[1] - 1, parts[2]);
    
    return dateObj.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
    });
}

function fetchTelemetry() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            // 1. Render Current Weather Panel
            document.getElementById('weather-temp').textContent = `${data.weather.temp_f}°F`;
            document.getElementById('weather-condition').textContent = data.weather.condition;
            document.getElementById('weather-humidity').textContent = `${data.weather.humidity}%`;
            document.getElementById('weather-wind').textContent = `${data.weather.wind_speed} mph`;

            const iconName = getIconFilename(data.weather.wmo_code, data.weather.is_day);
            document.getElementById('weather-icon-container').innerHTML = 
                `<object type="image/svg+xml" data="/static/weather-icons/${iconName}" class="weather-svg"></object>`;

            // 2. Render 7-Day Forecast Grid Panels
            const forecastContainer = document.getElementById('forecast-grid-container');
            forecastContainer.innerHTML = ''; // Wipe out previous loop fragments

            data.forecast.forEach((day, index) => {
                const dateLabel = index === 0 ? "Today" : parseForecastDate(day.date_raw);
                const forecastIcon = getIconFilename(day.wmo_code, 1); // Defaulting daytime icons for forecast list

                const dayHtml = `
                    <div class="forecast-day-item">
                        <div class="forecast-date">${dateLabel}</div>
                        <div class="forecast-icon-box">
                            <object type="image/svg+xml" data="/static/icons/${forecastIcon}" class="forecast-svg"></object>
                        </div>
                        <div class="forecast-temps">
                            <span class="high">${day.max_temp}°</span>
                            <span class="low">${day.min_temp}°</span>
                        </div>
                    </div>
                `;
                forecastContainer.insertAdjacentHTML('beforeend', dayHtml);
            });
        })
        .catch(error => console.error('Error fetching dashboard metrics:', error));
}

setInterval(updateClock, 1000);
setInterval(fetchTelemetry, 3000);

updateClock();
fetchTelemetry();
