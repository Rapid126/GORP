import json
from datetime import datetime

WEATHER_EVENTS_FILE = "weather_events.json"
MAP_SAMPLE_FILE = "map_sample.json"

def load_weather_events():
    try:
        with open(WEATHER_EVENTS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_weather_events(events):
    with open(WEATHER_EVENTS_FILE, "w") as f:
        json.dump(events, f, indent=4)

def load_map_sample():
    try:
        with open(MAP_SAMPLE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def get_detector_coordinates(detector_id):
    map_sample = load_map_sample()
    detectors = map_sample.get("detectors", [])
    for detector in detectors:
        if detector["detectorNumber"] == detector_id:
            return detector["coordinates"]
    return None  # Jeśli detektor nie został znaleziony

def add_weather_event(minute, detector_ids, temperature, wind, fog, rain):
    # Lista detektorów z ich współrzędnymi
    detectors_with_coordinates = []

    # Sprawdzamy każdy detektor
    for detector_id in detector_ids.split(","):
        detector_id = int(detector_id.strip())  # Usuwamy ewentualne spacje i konwertujemy na int
        coordinates = get_detector_coordinates(detector_id)

        if coordinates:
            detectors_with_coordinates.append({
                "detectorNumber": detector_id,
                "coordinates": coordinates
            })
        else:
            # Jeśli którykolwiek detektor nie jest na mapie, nie zapisujemy zdarzenia
            print(f"Detektor o ID {detector_id} nie występuje na mapie. Zdarzenie nie zostanie zapisane.")
            return  # Przerywamy funkcję, nie zapisując zdarzenia

    # Tworzymy event tylko wtedy, gdy wszystkie detektory zostały znalezione na mapie
    event = {
        "minute": minute,
        "detectorNumber": detector_ids,
        "temperature": temperature,
        "wind": wind,
        "fog": fog,
        "rain": rain,
        "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "detectors": detectors_with_coordinates
    }

    events = load_weather_events()
    events.append(event)
    save_weather_events(events)
    print(f"Zdarzenie pogodowe zapisane: {event}")
