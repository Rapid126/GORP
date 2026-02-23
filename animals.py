import random
from datetime import datetime
from datetime import timedelta

def create_animal_location(animal_id, longitude, latitude, timestamp):
    """
    Tworzy słownik reprezentujący lokalizację zwierzęcia.

    Args:
        animal_id (str): Identyfikator zwierzęcia.
        longitude (float): Współrzędna geograficzna (długość geograficzna).
        latitude (float): Współrzędna geograficzna (szerokość geograficzna).
        timestamp (str): Znacznik czasu w formacie "YYYY-MM-DD HH:MM:SS.ffffff".

    Returns:
        dict: Słownik zawierający dane o lokalizacji zwierzęcia.
    """
    return {
        "title": "animalLocation",
        "animalId": animal_id,
        "timeStamp": timestamp,
        "location": {
            "longitude": str(longitude),
            "latitude": str(latitude)
        }
    }


def generate_route_for_animal(animal_id, start_time, end_time, num_points,start_longitude=None,start_latitude=None):
    """
    Generuje trasę ruchu zwierzęcia jako listę punktów z przypisanymi znacznikami czasu.
    Trasa jest generowana jako losowy spacer zaczynający się od bazowej lokalizacji.

    Args:
        animal_id (str): Identyfikator zwierzęcia (używany przy generowaniu trasy, choć tu nie wpływa na punkty).
        start_time (datetime): Czas rozpoczęcia trasy.
        end_time (datetime): Czas zakończenia trasy.
        num_points (int): Liczba punktów, które mają zostać wygenerowane.
        start_latitude(float):startowy latiitute, jezeli none to random
        start_longitude(float):startowy longiute, jezeli none to random

    Returns:
        dict: Słownik zawierający klucz "route", który wskazuje na listę punktów trasy.
              Każdy punkt to słownik z kluczami: "timeStamp", "longitude" oraz "latitude".
    """

    route = []
    if num_points < 2:
        raise ValueError("Liczba punktów musi być co najmniej 2")

    total_seconds = (end_time - start_time).total_seconds()
    interval = total_seconds / (num_points - 1)

    #startowa lokacja, na razie statyczna
    base_longitude = start_longitude if start_longitude is not None else random.uniform(100.0, 1000.0)
    base_latitude = start_latitude if start_latitude is not None else random.uniform(100.0, 1000.0)

    current_lon = base_longitude
    current_lat = base_latitude

    for i in range(num_points):
        point_time = start_time + timedelta(seconds=i * interval)
        current_lon += random.uniform(-20.0, 20.0)
        current_lat += random.uniform(-20.0, 20.0)
        route.append({
            "timeStamp": point_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "longitude": current_lon,
            "latitude": current_lat
        })

    return {"route": route}

def get_location_from_route(route, current_time):
    """
    Wyznacza aktualną lokalizację na trasie w oparciu o zadany czas.
    Jeśli czas symulacji znajduje się między dwoma punktami, następuje interpolacja liniowa.

    Args:
        route (list): Lista punktów trasy, gdzie każdy punkt jest słownikiem z "timeStamp", "longitude" i "latitude".
        current_time (datetime): Aktualny czas symulacji.

    Returns:
        dict: Słownik zawierający "longitude" i "latitude" określone na podstawie aktualnego czasu.
    """
    if not route:
        return {"longitude": 0, "latitude": 0}

    # Pierwszy punkt
    first_time = datetime.strptime(route[0]["timeStamp"], "%Y-%m-%d %H:%M:%S.%f")
    if current_time <= first_time:
        return {"longitude": route[0]["longitude"], "latitude": route[0]["latitude"]}

    # Ostatni punkt
    last_time = datetime.strptime(route[-1]["timeStamp"], "%Y-%m-%d %H:%M:%S.%f")
    if current_time >= last_time:
        return {"longitude": route[-1]["longitude"], "latitude": route[-1]["latitude"]}

    # Wyszukaj przedział, w którym mieści się current_time
    for i in range(len(route) - 1):
        t1 = datetime.strptime(route[i]["timeStamp"], "%Y-%m-%d %H:%M:%S.%f")
        t2 = datetime.strptime(route[i + 1]["timeStamp"], "%Y-%m-%d %H:%M:%S.%f")
        if t1 <= current_time <= t2:
            # Oblicz współczynnik interpolacji
            total_diff = (t2 - t1).total_seconds()
            if total_diff == 0:
                factor = 0
            else:
                factor = (current_time - t1).total_seconds() / total_diff
            lon = route[i]["longitude"] + factor * (route[i + 1]["longitude"] - route[i]["longitude"])
            lat = route[i]["latitude"] + factor * (route[i + 1]["latitude"] - route[i]["latitude"])
            return {"longitude": lon, "latitude": lat}

    # W sytuacji awaryjnej zwróć ostatni punkt
    return {"longitude": route[-1]["longitude"], "latitude": route[-1]["latitude"]}


def generate_route_with_path(animal_id, start_time, end_time, num_points, path_points,start_longitude=None,start_latitude=None):
    """
    Generuje trasę ruchu zwierzęcia, w której wymusza się, aby przynajmniej raz
    przejechało przez podaną ścieżkę (lista punktów).

    Trasa jest tworzona jako losowy spacer, w którym na równych odstępach
    zastępujemy niektóre punkty wygenerowane losowo punktami ze ścieżki.

    Args:
        animal_id (str): Identyfikator zwierzęcia.
        start_time (datetime): Czas rozpoczęcia trasy.
        end_time (datetime): Czas zakończenia trasy.
        num_points (int): Liczba punktów trasy.
        path_points (list): Lista punktów ścieżki do wymuszenia.
                            Każdy punkt powinien być słownikiem z przynajmniej
                            kluczami "longitude" oraz "latitude".

    Returns:
        dict: Słownik zawierający klucz "route" z listą punktów. Każdy punkt to
              słownik z kluczami: "timeStamp", "longitude", "latitude".
    """


    if num_points < len(path_points):
        raise ValueError("Liczba punktów trasy nie może być mniejsza niż liczba punktów ścieżki.")

    route = []
    total_seconds = (end_time - start_time).total_seconds()
    interval = total_seconds / (num_points - 1)

    # Początkowa, bazowa lokalizacja – można ustawić losowo lub jako w poprzedniej funkcji.
    base_longitude = start_longitude if start_longitude is not None else random.uniform(100.0, 1000.0)
    base_latitude = start_latitude if start_latitude is not None else random.uniform(100.0, 1000.0)

    current_lon = base_longitude
    current_lat = base_latitude

    # Wyliczamy, w których pozycjach trasy wstawimy punkty ścieżki.
    num_path_points = len(path_points)
    # Rozkładamy punkty ścieżki równomiernie w całej trasie.
    path_indices = [int(i * (num_points - 1) / (num_path_points - 1)) for i in range(num_path_points)]

    for i in range(num_points):
        point_time = start_time + timedelta(seconds=i * interval)
        # Jeśli aktualny indeks jest jednym z wyznaczonych dla ścieżki – wstaw punkt ze ścieżki.
        if i in path_indices:
            # Znajdujemy odpowiadający indeks w liście path_points
            path_idx = path_indices.index(i)
            lon = path_points[path_idx]["longitude"]
            lat = path_points[path_idx]["latitude"]
        else:
            # Generujemy losowo
            current_lon += random.uniform(-20.0, 20.0)
            current_lat += random.uniform(-20.0, 20.0)
            lon = current_lon
            lat = current_lat

        route.append({
            "timeStamp": point_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "longitude": lon,
            "latitude": lat
        })

    return {"route": route}