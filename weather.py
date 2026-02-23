import json
import os
import random
from datetime import datetime, timedelta

def load_weather_events(file_path="weather_events.json"):
    """Ładowanie zdarzeń pogodowych z pliku JSON."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return sorted(json.load(f), key=lambda e: e["minute"])

def save_weather_events(events, file_path="weather_events.json"):
    """Zapisanie zdarzeń pogodowych do pliku JSON."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=4)

def interpolate(a, b, ratio):
    """Interpolacja liniowa między dwoma wartościami."""
    return a + (b - a) * ratio

def apply_variation(value, variation_percent=3):
    """Dodanie losowej fluktuacji do wartości."""
    variation = value * (variation_percent / 100.0)
    return round(value + random.uniform(-variation, variation), 2)

def smooth_weather_transition(e1, e2, minute):
    """Płynna interpolacja między dwoma zdarzeniami pogodowymi."""
    if e2["minute"] == e1["minute"]:
        ratio = 1
    else:
        ratio = (minute - e1["minute"]) / (e2["minute"] - e1["minute"])

    interpolated_values = {
        "temperature": interpolate(e1["temperature"], e2["temperature"], ratio),
        "wind": interpolate(e1["wind"], e2["wind"], ratio),
        "fog": interpolate(e1["fog"], e2["fog"], ratio),
        "rain": interpolate(e1["rain"], e2["rain"], ratio),
    }

    return {
        key: apply_variation(value, variation_percent=3)
        for key, value in interpolated_values.items()
    }

def get_weather_for_detector(minute, detector_number, events):
    """Zwraca dane pogodowe dla konkretnego detektora w danej minucie."""
    relevant_events = [e for e in events if str(detector_number) in [str(d["detectorNumber"]) for d in e["detectors"]]]

    if not relevant_events:
        return {
            "temperature": apply_variation(10.0),
            "wind": apply_variation(5.0),
            "fog": apply_variation(0.0),
            "rain": apply_variation(0.0),
        }

    earlier = [e for e in relevant_events if e["minute"] <= minute]
    later = [e for e in relevant_events if e["minute"] > minute]

    if earlier and later:
        e1 = earlier[-1]
        e2 = later[0]
        weather = smooth_weather_transition(e1, e2, minute)
    elif earlier:
        e1 = earlier[-1]
        weather = {
            "temperature": apply_variation(e1["temperature"], 3),
            "wind": apply_variation(e1["wind"], 10),
            "fog": apply_variation(e1["fog"], 10),
            "rain": apply_variation(e1["rain"], 10),
        }
    else:
        e2 = later[0]
        weather = {
            "temperature": apply_variation(e2["temperature"], 3),
            "wind": apply_variation(e2["wind"], 10),
            "fog": apply_variation(e2["fog"], 10),
            "rain": apply_variation(e2["rain"], 10),
        }

    return weather

def get_timestamp_for_minute(minute):
    """Generuje timeStamp na podstawie minuty od bazowej daty."""
    base_date = datetime(2020, 11, 8, 0, 0)  # Bazowa data
    target_time = base_date + timedelta(minutes=minute)
    return target_time.strftime("%Y-%m-%d %H:%M:%S.%f")

def save_weather_station_to_file(weather_station, file_path="weather_station.json"):
    """Zapisuje dane pogodowe do pliku JSON w wymaganym formacie."""
    formatted_data = []
    for item in weather_station:
        formatted_item = {
            "title": "WS",
            "stationId": f"station-{item['detectorNumber']:04d}",  # Format: station-XXXX
            "timeStamp": get_timestamp_for_minute(item.get("minute", 0)),  # Dodajemy minutę, jeśli dostępna
            "location": {
                "longitude": str(item["coordinates"]["longitude"]),  # Konwersja na string
                "latitude": str(item["coordinates"]["latitude"])     # Konwersja na string
            },
            "wind": str(item["weather"]["wind"]),                   # Konwersja na string
            "fog": str(item["weather"]["fog"]),                     # Konwersja na string
            "temperature": str(item["weather"]["temperature"]),     # Konwersja na string
            "rain": str(item["weather"]["rain"])                    # Konwersja na string
        }
        formatted_data.append(formatted_item)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(formatted_data, f, indent=4)

def get_weather_by_minute(minute, file_path="weather_events.json"):
    """Pobiera dane pogodowe dla wszystkich detektorów na danej minucie."""
    all_events = load_weather_events(file_path)
    future_events = [e for e in all_events if e["minute"] >= minute]
    save_weather_events(all_events, file_path)

    unique_detectors = {}
    for e in all_events:
        for d in e["detectors"]:
            unique_detectors[d["detectorNumber"]] = d["coordinates"]

    result = []
    for detector_number, coordinates in unique_detectors.items():
        weather = get_weather_for_detector(minute, detector_number, all_events)
        result.append({
            "detectorNumber": detector_number,
            "coordinates": coordinates,
            "weather": weather,
            "minute": minute  # Dodajemy minutę do wyniku, aby użyć w save_weather_station_to_file
        })

    return result