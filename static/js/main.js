// Function to handle continuous live system clock time updates
function updateClock() {
    const now = new Date();
    
    // Format Time: 12-hour format with AM/PM
    document.getElementById('current-time').textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    });

    // Format Date: e.g., Wednesday, September 9, 2026
    document.getElementById('current-date').textContent = now.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Function to choose the right Meteocons file based on WMO code and Day/Night flag
function getIconFilename(wmoCode, isDay) {
    if (wmoCode === 0) {
        return isDay ? 'clear-day.svg' : 'clear-night.svg';
    } else if (wmoCode >= 1 && wmoCode <= 3) {
        return isDay ? 'partly-cloudy-day.svg' : 'partly-cloudy-night.svg';
    } else if (wmoCode >= 45 && wmoCode <= 48) {
        return 'fog.svg';
    } else if ((wmoCode >= 51 && wmoCode <= 67) || (wmoCode >= 80 && wmoCode <= 82)) {
        return 'rain.svg';
    } else if ((wmoCode >= 71 && wmoCode <= 77) || (wmoCode >= 85 && wmoCode <= 86)) {
        return 'snow.svg';
    } else if (wmoCode >= 95) {
        return 'thunderstorms.svg';
    }
    return 'not-available.svg';
}

// Function to fetch real-time Telemetry endpoints from the Flask server
function fetchTelemetry() {
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            // Update UI elements
            document.getElementById('weather-temp').textContent = data.weather.temp;
            document.getElementById('weather-condition').textContent = data.weather.meta;

            // Generate path to the correct animated Meteocon SVG file
            const iconName = getIconFilename(data.weather.wmo_code, data.weather.is_day);
            const iconUrl = `/static/weather-icons/${iconName}`;

            // Inject the animated SVG as an object element to maintain dynamic CSS properties
            const container = document.getElementById('weather-icon-container');
            container.innerHTML = `<object type="image/svg+xml" data="${iconUrl}" class="weather-svg"></object>`;
        })
        .catch(error => console.error('Error fetching dashboard telemetry:', error));
}

// Intervals configuration
setInterval(updateClock, 1000);     // Refresh time strings every 1 second
setInterval(fetchTelemetry, 3000); // Poll backend telemetry framework data every 3 seconds

// Initial execution blocks
updateClock();
fetchTelemetry();
