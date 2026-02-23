import json


def create_map_with_details(map_name, routes, detectors, bts_stations, special_places, raster_map):
    """
    Tworzy JSON mapy z wieloma ścieżkami, detektorami, stacjami BTS, specjalnymi miejscami oraz informacjami o mapie rastrowej.

    :param map_name: Nazwa mapy (string)
    :param routes: Lista tras, gdzie każda trasa to słownik zawierający:
        - "points": lista krotek (longitude, latitude)
        - "number": numer trasy (int)
        - "difficulty": trudność trasy (int)
        - "color": kolor trasy (string)
        - "is_entrance": czy trasa jest wejściem (bool)
        - "area": obszar (string)
    :param detectors: Lista detektorów, gdzie każdy detektor to słownik z kluczami:
        - "detectorNumber": numer detektora (int)
        - "coordinates": krotka (longitude, latitude)
    :param bts_stations: Lista stacji BTS, gdzie każda stacja to słownik z kluczami:
        - "stationNumber": numer stacji (int)
        - "coordinates": krotka (longitude, latitude)
    :param special_places: Lista specjalnych miejsc, gdzie każde miejsce to słownik z kluczami:
        - "placeNumber": numer miejsca (int)
        - "coordinates": krotka (longitude, latitude)
        - "radius": promień miejsca (float)
    :param raster_map: Słownik z informacjami o mapie rastrowej zawierający klucze:
        - "topLeftLatLon": słownik z kluczami "a" (latitude) i "b" (longitude)
        - "downRightLatLon": słownik z kluczami "a" (latitude) i "b" (longitude)
        - "canvasWidthHeight": słownik z kluczami "a" (szerokość) i "b" (wysokość)
    :return: JSON w postaci słownika
    """
    return {
        "mapName": map_name,
        "routes": [
            {
                "points": [
                    {
                        "longitude": point[0],
                        "latitude": point[1],
                        "point": index + 1
                    } for index, point in enumerate(route["points"])
                ],
                "number": route["number"],
                "difficulty": route["difficulty"],
                "color": route["color"],
                "isEntrance": route["is_entrance"],
                "area": route["area"]
            } for route in routes
        ],
        "detectors": [
            {
                "detectorNumber": detector["detectorNumber"],
                "coordinates": {
                    "longitude": detector["coordinates"][0],
                    "latitude": detector["coordinates"][1]
                }
            } for detector in detectors
        ],
        "btsStations": [
            {
                "stationNumber": station["stationNumber"],
                "coordinates": {
                    "longitude": station["coordinates"][0],
                    "latitude": station["coordinates"][1]
                }
            } for station in bts_stations
        ],
        "specialPlaces": [
            {
                "placeNumber": place["placeNumber"],
                "coordinates": {
                    "longitude": place["coordinates"][0],
                    "latitude": place["coordinates"][1]
                },
                "radius": place["radius"]
            } for place in special_places
        ],
        "rasterMap": {
            "topLeftLatLon": {
                "a": raster_map["topLeftLatLon"]["a"],
                "b": raster_map["topLeftLatLon"]["b"]
            },
            "downRightLatLon": {
                "a": raster_map["downRightLatLon"]["a"],
                "b": raster_map["downRightLatLon"]["b"]
            },
            "canvasWidthHeight": {
                "a": raster_map["canvasWidthHeight"]["a"],
                "b": raster_map["canvasWidthHeight"]["b"]
            }
        }
    }


def create_map_sample():
    example_map_name = "The Tatra Mountains TEST bazy"
    example_routes = [
        {
            "points": [
                (563.0, 282.0),
                (581.0, 282.0),
                (612.0, 305.0),
                (673.0, 293.0),
                (703.0, 306.0),
                (720.0, 300.0),
                (735.0, 309.0),
                (749.0, 265.0),
                (745.0, 217.0)
            ],
            "number": 1,
            "difficulty": 2,
            "color": "Chocolate",
            "is_entrance": False,
            "area": "Tatry wysokie"
        },
        {
            "points": [
                (927.0, 198.0),
                (745.0, 218.0)
            ],
            "number": 2,
            "difficulty": 3,
            "color": "CornflowerBlue",
            "is_entrance": True,
            "area": "Tatry zachodnie"
        }
    ]
    example_detectors = [
        {"detectorNumber": 1, "coordinates": (558.0, 139.0)},
        {"detectorNumber": 2, "coordinates": (165.0, 274.0)},
        {"detectorNumber": 3, "coordinates": (635.0, 298.0)}
    ]
    example_bts_stations = [
        {"stationNumber": 1, "coordinates": (24.0, 466.0)}
    ]
    example_special_places = [
        {"placeNumber": 1, "coordinates": (648.0, 289.0), "radius": 30.0}
    ]
    example_raster_map = {
        "topLeftLatLon": {"a": 12.3, "b": 32.1},
        "downRightLatLon": {"a": 12.4, "b": 32.2},
        "canvasWidthHeight": {"a": 1280, "b": 700}
    }

    result = create_map_with_details(
        example_map_name,
        example_routes,
        example_detectors,
        example_bts_stations,
        example_special_places,
        example_raster_map
    )
    return result

