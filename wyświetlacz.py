# Aby uruchomić wyświetlacz trzeba w cmd w lokalizacji projektu (czyli folder GOPR_symulator)
# wykonać poniższą komendę
#
# python -m http.server 8000
#
# Następnie uruchomić ten plik
# Od tej chwili mapa dostępna jest pod linkiem:
#
# http://localhost:8000/map.html
#
# Na ten moment aktualizuje się co 10 sekund później dostosuje się to do prędkości generowania
import json

# Wczytaj dane z pliku map_sample.json
with open("map_sample.json", "r") as file:
    static_data = json.load(file)

# Ścieżka do obrazka mapy
map_file = "krakow.png"

# HTML - szkielet pliku
html_template = f"""
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mapa symulacji</title>
    <style>
        canvas {{
            border: 1px solid black;
        }}
    </style>
</head>
<body>
    <h1>Mapa tras i lokalizacji zwierząt</h1>
    <canvas id="mapCanvas"></canvas>
    <div id="weatherDataContainer">
        <h2>Stacje pogodowe</h2>
        <table id="weatherTable" border="1">
            <thead>
                <tr>
                    <th>Identyfikator</th>
                    <th>Czas</th>
                    <th>Temperatura (°C)</th>
                    <th>Wiatr (km/h)</th>
                    <th>Mgła</th>
                    <th>Deszcz (mm)</th>
                </tr>
            </thead>
            <tbody>
                <!-- Wiersze będą generowane dynamicznie -->
            </tbody>
        </table>
    </div>
    <script>
        const mapImageSrc = "{map_file}";

        // Funkcja do rysowania punktów
        function drawPoint(ctx, x, y, color = "red", radius = 5, label = "") {{
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.closePath();

            // Dodaj etykiety do punktów
            if (label) {{
                ctx.font = "12px Arial";
                ctx.fillStyle = "black";
                ctx.fillText(label, x + radius + 2, y);
            }}
        }}

        // Funkcja do rysowania tras (linii między punktami)
        function drawLine(ctx, points, color = "red", width = 4) {{
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = width;

            ctx.moveTo(points[0].longitude, points[0].latitude);
            points.forEach(point => {{
                ctx.lineTo(point.longitude, point.latitude);
            }});

            ctx.stroke();
            ctx.closePath();
        }}

        // Funkcja do rysowania mapy
        async function drawMap() {{
            const canvas = document.getElementById("mapCanvas");
            const ctx = canvas.getContext("2d");

            const mapImage = new Image();
            mapImage.src = mapImageSrc;
            await new Promise(resolve => mapImage.onload = resolve);

            canvas.width = mapImage.width;
            canvas.height = mapImage.height;

            ctx.drawImage(mapImage, 0, 0);

            // Wczytaj dane statyczne z map_sample.json
            const staticData = {json.dumps(static_data)};
            staticData.routes.forEach(route => {{
                const points = route.points;
                const lineColor = route.color;

                drawLine(ctx, points, lineColor, 4); // Rysowanie linii
                points.forEach(point => {{
                    drawPoint(ctx, point.longitude, point.latitude, "red", 3, route.animalId); // Rysowanie punktów
                }});
            }});

            // Rysowanie detektorów
            staticData.detectors.forEach(detector => {{
                drawPoint(ctx, detector.coordinates.longitude, detector.coordinates.latitude, "blue", 5);
            }});

            // Rysowanie stacji BTS
            staticData.btsStations.forEach(station => {{
                drawPoint(ctx, station.coordinates.longitude, station.coordinates.latitude, "green", 5);
            }});

            // Rysowanie miejsc specjalnych
            staticData.specialPlaces.forEach(place => {{
                const x = place.coordinates.longitude;
                const y = place.coordinates.latitude;
                const radius = place.radius;
                ctx.beginPath();
                ctx.arc(x, y, radius, 0, 2 * Math.PI);
                ctx.strokeStyle = "yellow";
                ctx.lineWidth = 2;
                ctx.stroke();
                ctx.closePath();
            }});

            // Wczytaj dane dynamiczne z plików JSON
            const locationsResponse = await fetch("animal_locations.json");
            const routesResponse = await fetch("animal_routes.json");

            const animalLocations = await locationsResponse.json();
            const animalRoutes = await routesResponse.json();

            const locationsResponseT = await fetch("tourist_location.json");
            const touristLocations = await locationsResponseT.json();

            // Rysowanie lokalizacji zwierząt
            animalLocations.forEach(location => {{
                drawPoint(ctx, parseFloat(location.location.longitude), parseFloat(location.location.latitude), "blue", 5, location.animalId);
            }});

            // Rysowanie lokalizacji turystów
            touristLocations.forEach(location => {{
                drawPoint(ctx, parseFloat(location.location.longitude), parseFloat(location.location.latitude), "red", 5, location.PhoneId);
            }});

            // Rysowanie tras zwierząt
            animalRoutes.forEach(route => {{
                const points = route.route.map(r => ({{
                    longitude: parseFloat(r.location.longitude),
                    latitude: parseFloat(r.location.latitude)
                }}));
                drawLine(ctx, points, "green", 2);
                points.forEach(point => {{
                    drawPoint(ctx, point.longitude, point.latitude, "yellow", 4, route.animalId);
                }});
            }});
        }}

        // Funkcja do załadowania danych pogodowych i uzupełnienia tabeli
async function populateWeatherTable() {{
    const response = await fetch("weather_data.json");
    const weatherData = await response.json();

    const tableBody = document.querySelector("#weatherTable tbody");
    tableBody.innerHTML = ""; // Wyczyść zawartość tabeli przed aktualizacją

    weatherData.forEach(station => {{
        const row = document.createElement("tr");

        row.innerHTML = `
        <td>${{station.detectorNumber}}</td>
        <td>${{station.coordinates.latitude}}, ${{station.coordinates.longitude}}</td>
        <td>${{station.weather.temperature}}</td>
        <td>${{station.weather.wind}}</td>
        <td>${{station.weather.fog}}</td>
        <td>${{station.weather.rain}}</td>
    `;

        tableBody.appendChild(row);
    }});
}}

// Wywołanie funkcji przy ładowaniu strony
populateWeatherTable();
setInterval(populateWeatherTable, 10000); // Aktualizacja danych co 10 sekund


        // Aktualizacja mapy co 10 sekund
        drawMap();
        setInterval(drawMap, 10000);
    </script>
</body>
</html>
"""

# Zapisz plik HTML
with open("map.html", "w", encoding="utf-8") as html_file:
    html_file.write(html_template)

print("Plik HTML z dynamiczną mapą został wygenerowany: map.html")
