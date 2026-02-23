import json
import math
import random
import threading
import time
import os
from datetime import datetime, timedelta
from DBConnector import DBConnector
from animals import (
    create_animal_location,
    generate_route_for_animal,
    get_location_from_route,
    generate_route_with_path
)
from routes import create_map_sample
import tourists
from weather import get_weather_by_minute, save_weather_station_to_file
from weather_events import load_weather_events
import simulation_db


class Simulation:
    def __init__(self, config_file="config.json"):
        self.map_conflict = False
        self.bts_stations = []
        self.raster_map = None
        self.map_name = None
        self.special_places = []
        self.running = False
        self.thread = None
        self.delay_seconds = 10
        self.load_config(config_file)
        self.animal_routes = {}
        self.tourists_dict = {}
        self.weather_events = load_weather_events()
        self.routes = []
        self.entrances = []
        self.db = DBConnector()
        self.save_to_db = False  # domyślnie nie zapisujemy do bazy

    def load_config(self, config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.animals = config.get("animals", [])
        self.animal_ids = [f"{animal['type']}-{i:04}" for i, animal in enumerate(self.animals, start=1)]
        self.time_multiplier = config.get("time_multiplier", 1.0)
        self.tourist_spawn_chance = config.get("tourist_spawn_chance", 10)

        start_time_str = config.get("start_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.initial_sim_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        self.sim_time = self.initial_sim_time

        duration_hours = config.get("duration_hours", 1)
        self.end_sim_time = self.initial_sim_time + timedelta(hours=duration_hours)

    def setup(self):
        if not os.path.exists("map_sample.json"):
            map_sample = create_map_sample()
            with open("map_sample.json", "w", encoding="utf-8") as f:
                json.dump(map_sample, f, indent=4)
        else:
            with open("map_sample.json", "r", encoding="utf-8") as f:
                map_sample = json.load(f)

        self.map_name = map_sample.get("mapName")
        self.raster_map = map_sample.get("rasterMap")
        self.special_places = map_sample["specialPlaces"]
        self.bts_stations = map_sample["btsStations"]
        self.routes = map_sample["routes"]
        self.entrances = [r for r in self.routes if r.get("isEntrance", False)]
        for e in self.entrances:
            if "number" not in e:
                raise ValueError(f"Trasa wejściowa {e} nie ma klucza 'number'")

        if self.save_to_db:
            # DODAWANIE MAPY DO BAZY, GDY TAKIEJ NIE MA
            self.map_conflict = simulation_db.check_map_conflict(self.db, self.map_name)
            if not self.map_conflict:
                print("Dodaje nową mapę")
                canvas_w = self.raster_map["canvasWidthHeight"]["a"]
                canvas_h = self.raster_map["canvasWidthHeight"]["b"]
                simulation_db.insert_map(self.db, self.map_name, canvas_w, canvas_h)

                next_place_id = simulation_db.get_first_index_of(self.db, "place_id", "special_place")
                num = 1
                for place in self.special_places:
                    simulation_db.insert_special_place(self.db, next_place_id, place.get("radius"),
                                                       place.get("coordinates", {}).get("longitude"),
                                                       place.get("coordinates", {}).get("longitude"))
                    simulation_db.link_special_place_to_map(self.db, next_place_id, self.map_name, num)
                    next_place_id += 1
                    num += 1

                next_bts_id = simulation_db.get_first_index_of(self.db, "bts_station_id", "bts_station")
                num = 1
                for bts in self.bts_stations:
                    simulation_db.insert_bts_station(self.db, next_bts_id, bts.get("coordinates", {}).get("longitude"),
                                                     bts.get("coordinates", {}).get("longitude"))
                    simulation_db.link_bts_station_to_map(self.db, next_bts_id, self.map_name, num)
                    next_bts_id += 1
                    num += 1

                with open("map_sample.json", "r") as f:
                    map_data = json.load(f)

                map_name = map_data["mapName"]
                for route in map_data["routes"]:
                    simulation_db.insert_route_with_points(self.db, map_name, route)

            simulation_db.insert_simulated_map(self.db, self.next_id, self.map_name)
        else:
            self.map_conflict = True  # żeby uniknąć użycia w run()

        end_time = self.initial_sim_time + timedelta(hours=1)
        NUM_POINTS = 100
        for aid, animal in zip(self.animal_ids, self.animals):
            rn = animal.get("route_number", 0)
            if rn:
                pts = next(r for r in map_sample["routes"] if r["number"] == rn)["points"]
                rd = generate_route_with_path(
                    aid, self.initial_sim_time, end_time,
                    NUM_POINTS, pts,
                    start_longitude=animal.get("start_longitude"),
                    start_latitude=animal.get("start_latitude")
                )
            else:
                rd = generate_route_for_animal(
                    aid, self.initial_sim_time, end_time,
                    NUM_POINTS,
                    start_longitude=animal.get("start_longitude"),
                    start_latitude=animal.get("start_latitude")
                )
            self.animal_routes[aid] = rd["route"]

    def run(self):
        self.setup()
        location_sim = ActorsLocationSimulator(self)
        link_to_map = not self.map_conflict if self.save_to_db else False

        if self.save_to_db:
            curr_reading_id = simulation_db.get_first_index_of(self.db, "reading_id", "weather_reading")
        else:
            curr_reading_id = None

        while self.running and self.sim_time <= self.end_sim_time:
            minute_of_sim = int((self.sim_time - self.initial_sim_time).total_seconds() / 60)
            weather_station = get_weather_by_minute(minute_of_sim)
            save_weather_station_to_file(weather_station)

            if self.save_to_db:
                try:
                    with open("weather_station.json", "r", encoding="utf-8") as f:
                        weather_station_init_data = json.load(f)

                    for station in weather_station_init_data:
                        conflict = simulation_db.check_weather_station_conflict(self.db, station["stationId"])
                        if not conflict:
                            simulation_db.insert_weather_station(self.db, station)
                            link_to_map = True
                        if link_to_map:
                            simulation_db.link_weather_station_to_map(self.db, station, self.map_name)
                            link_to_map = False
                        simulation_db.insert_weather_record(
                            self.db, station, self.sim_time, self.next_id, curr_reading_id
                        )
                        curr_reading_id += 1
                except Exception as e:
                    print(f"[BŁĄD POGODY] {e}")

            location_sim.start_updating_animal_locations(self.delay_seconds)

            # generowanie turystów
            for e in self.entrances:
                if random.uniform(0, 100) < e.get("spawn_chance", self.tourist_spawn_chance):
                    new_phone = f"+48{random.randint(100000000, 999999999)}"
                    t = tourists.Tourist(new_phone, route_number=e["number"])
                    lon, lat = e["points"][0]["longitude"], e["points"][0]["latitude"]
                    t.set_coordinates(lon, lat, e["number"], 0)
                    self.tourists_dict[new_phone] = t
                    if self.save_to_db:
                        t.insert_tourist_into_database(self.next_id, self.db)

            tourists_list = list(self.tourists_dict.values())
            timestamp = location_sim.get_timestamp()
            location_sim.start_updating_tourist_locations(self.delay_seconds)

            with open("tourist_location.json", "w", encoding="utf-8") as f:
                json.dump([
                    t.create_location(
                        longitude=t.last_location[0],
                        latitude=t.last_location[1],
                        loc_type="GPS" if t.gps_enabled else "BTS",
                        timestamp=timestamp
                    ) for t in tourists_list
                ], f, indent=4)

            if self.save_to_db and tourists_list:
                with open("tourist_location.json", "r", encoding="utf-8") as f:
                    tourists_j = json.load(f)

                loc_id_start = simulation_db.get_first_index_of_location(self.db)
                simulation_db.bulk_insert_tourist_locations(
                    self.db, self.next_id, tourists_j, loc_id_start
                )

            print(f"[SIM TIME] {self.sim_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.sim_time += timedelta(seconds=self.delay_seconds)
            time.sleep(self.delay_seconds / self.time_multiplier)

        self.stop()

    def start(self):
        if not self.running:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)

            if self.save_to_db:
                if not self.db.connection:
                    self.db.connect()
                    self.next_id = simulation_db.get_first_index(self.db)

                start_dt = datetime.strptime(cfg["start_time"], "%Y-%m-%d %H:%M:%S")
                dur_td = timedelta(hours=cfg["duration_hours"])
                dur_time = (datetime.min + dur_td).time()
                end_dt = start_dt + dur_td
                end_epoch = end_dt.strftime("%Y-%m-%d %H:%M:%S")

                # Wstawienie rekordu symulacji
                simulation_db.insert_simulation(self.db, self.next_id, start_dt, dur_time, end_epoch)

                # Wstawienie zwierząt i powiązań
                for aid in self.animal_ids:
                    simulation_db.insert_animal(self.db, aid)
                    simulation_db.link_animal_to_simulation(self.db, aid, self.next_id)

            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
            print("Symulacja rozpoczęta.")

    def stop(self):
        if self.running:
            self.running = False
            print("Symulacja zatrzymana.")

    def reset(self):
        self.stop()
        self.load_config("config.json")
        self.sim_time = self.initial_sim_time
        self.tourists_dict.clear()
        self.animal_routes = {}
        if self.db.connection:
            self.db.disconnect()
        for fname in ("animal_locations.json", "tourist_location.json"):
            with open(fname, "w", encoding="utf-8") as f:
                json.dump([], f)
        print("Symulacja została zresetowana.")

    def get_elapsed_time(self):
        return (self.sim_time - self.initial_sim_time).total_seconds()

    def get_total_duration(self):
        return (self.end_sim_time - self.initial_sim_time).total_seconds()

    @property
    def is_running(self):
        return self.running

    def set_time_multiplier(self, new_multiplier: float):
        self.time_multiplier = new_multiplier
        print(f"[SIMULATION] Nowy mnożnik czasu: {new_multiplier}")



class ActorsLocationSimulator:
    def __init__(self, simulation):
        self.simulation = simulation
        self.bts_stations = []

    def get_timestamp(self):
        return self.simulation.sim_time.strftime("%Y-%m-%d %H:%M:%S.%f")

    def start_updating_tourist_locations(self, delta):
        tourists = list(self.simulation.tourists_dict.values())
        self.update_tourists_locations(delta, tourists)
        self.determine_signal_strength()
        self.update_gps_coordinates()
        self.update_nearest_detector(tourists)

    def update_tourists_locations(self, delta, tourists):
        for tourist in tourists:
            self.manage_tourist_movement(tourist, delta)
            self.manage_leaving_the_map(tourist)

    def manage_tourist_movement(self, tourist, delta):
        tourist.check_special_places(self.simulation.special_places)
        if not tourist.is_moving:
            return
        tourist.should_get_injured()
        tourist.should_get_lost_or_find_way()

        if tourist.is_lost:
            self.move_tourist_randomly(tourist, delta)
            return

        route = next(
            (r for r in self.simulation.routes if r["number"] == tourist.current_route_number),
            None
        )
        if not route:
            print(f"Brak trasy {tourist.current_route_number} dla turysty {tourist.phone_id}")
            return

        route_points = route["points"]
        from_point = route_points[tourist.current_point_index]
        next_index = tourist.current_point_index + tourist.direction

        if 0 <= next_index < len(route_points):
            to_point = route_points[next_index]
            new_location = self.calculate_next_point(tourist, tourist.get_last_location(), to_point, delta)
            if new_location == [to_point["longitude"], to_point["latitude"]]:
                tourist.set_coordinates(new_location[0], new_location[1], tourist.current_route_number, next_index)
            else:
                tourist.set_coordinates(new_location[0], new_location[1], tourist.current_route_number, tourist.current_point_index)
        else:
            self.manage_crossings(tourist, route)

    def move_tourist_randomly(self, tourist, delta):
        tourist.update_speed()
        speed = tourist.current_speed
        distance = delta * speed

        current_location = tourist.get_last_location()

        # Losowy kierunek ruchu
        random_angle = random.uniform(0, 2 * 3.14159)  # Random angle in radians
        dx = distance * math.cos(random_angle)
        dy = distance * math.sin(random_angle)

        new_x = current_location[0] + dx
        new_y = current_location[1] + dy

        tourist.set_coordinates(new_x, new_y, tourist.current_route_number, tourist.current_point_index)
    def calculate_next_point(self, tourist, from_point, to_point, delta):
        tourist.update_speed()
        speed = tourist.current_speed
        distance = delta * speed
        current_location = from_point if isinstance(from_point, list) else [from_point["longitude"], from_point["latitude"]]

        target_location = [to_point["longitude"], to_point["latitude"]]

        dx = target_location[0] - current_location[0]
        dy = target_location[1] - current_location[1]
        total_distance = (dx**2 + dy**2)**0.5

        if total_distance <= distance or total_distance < 1e-6:
            return target_location
        else:
            ratio = distance / total_distance
            new_x = current_location[0] + dx * ratio
            new_y = current_location[1] + dy * ratio
            return [new_x, new_y]

    def find_nearby_routes(self, current_route_number, current_point):
        """Znajduje szlaki, których punkty początkowe lub końcowe są blisko danego punktu."""
        MAX_DISTANCE = 10.0  # Maksymalna odległość w pikselach
        nearby_routes = []

        current_x = current_point["longitude"]
        current_y = current_point["latitude"]

        for route in self.simulation.routes:
            if route["number"] == current_route_number:
                continue

            points = route["points"]
            start_point = points[0]
            end_point = points[-1]

            # Sprawdź odległość do punktu początkowego
            start_distance = ((current_x - start_point["longitude"])**2 + (current_y - start_point["latitude"])**2)**0.5
            if start_distance <= MAX_DISTANCE:
                nearby_routes.append({
                    "route_number": route["number"],
                    "point_index": 0,
                    "direction": 1  # Idzie w przód
                })

            # Sprawdź odległość do punktu końcowego
            end_distance = ((current_x - end_point["longitude"])**2 + (current_y - end_point["latitude"])**2)**0.5
            if end_distance <= MAX_DISTANCE:
                nearby_routes.append({
                    "route_number": route["number"],
                    "point_index": len(points) - 1,
                    "direction": -1  # Idzie wstecz
                })

        return nearby_routes

    def manage_crossings(self, tourist, current_route):
        route_points = current_route["points"]

        # Turysta dotarł do końca trasy (kierunek w przód)
        if tourist.direction == 1 and tourist.current_point_index == len(route_points) - 1:
            nearby_routes = self.find_nearby_routes(current_route["number"], route_points[-1])
            if nearby_routes:
                # Wybierz losowo inny szlak z pobliskich
                new_route_info = random.choice(nearby_routes)
                new_route_number = new_route_info["route_number"]
                new_route = next(r for r in self.simulation.routes if r["number"] == new_route_number)

                new_point_index = new_route_info["point_index"]
                new_direction = new_route_info["direction"]

                tourist.set_coordinates(
                    new_route["points"][new_point_index]["longitude"],
                    new_route["points"][new_point_index]["latitude"],
                    new_route_number,
                    new_point_index
                )
                tourist.set_direction(new_direction)
                print(f"Turysta {tourist.phone_id} przeszedł z trasy {current_route['number']} na trasę {new_route_number}")
                return

            # Jeśli nie ma pobliskich szlaków, turysta zawraca
            tourist.set_direction(-1)
            print(f"Turysta {tourist.phone_id} zawrócił na trasie {current_route['number']} (koniec trasy)")

        # Turysta dotarł do początku trasy (kierunek w tył)
        elif tourist.direction == -1 and tourist.current_point_index == 0:
            if current_route.get("isEntrance", False):
                # Wyjście z mapy tylko na początku tras wejściowych
                tourist.stats["exit_time"] = datetime.now()
                tourist.stats["exit_type"] = "normal_exit"
                print(f"Turysta {tourist.phone_id} opuścił mapę na początku trasy {current_route['number']}")
                del self.simulation.tourists_dict[tourist.phone_id]
            else:
                nearby_routes = self.find_nearby_routes(current_route["number"], route_points[0])
                if nearby_routes:
                    # Wybierz losowo inny szlak z pobliskich
                    new_route_info = random.choice(nearby_routes)
                    new_route_number = new_route_info["route_number"]
                    new_route = next(r for r in self.simulation.routes if r["number"] == new_route_number)

                    new_point_index = new_route_info["point_index"]
                    new_direction = new_route_info["direction"]

                    tourist.set_coordinates(
                        new_route["points"][new_point_index]["longitude"],
                        new_route["points"][new_point_index]["latitude"],
                        new_route_number,
                        new_point_index
                    )
                    tourist.set_direction(new_direction)
                    print(f"Turysta {tourist.phone_id} przeszedł z trasy {current_route['number']} na trasę {new_route_number}")
                    return

                # Jeśli nie ma pobliskich szlaków, turysta zawraca
                tourist.set_direction(1)
                print(f"Turysta {tourist.phone_id} zawrócił na trasie {current_route['number']} (początek trasy)")

    def manage_leaving_the_map(self, tourist):
        # Metoda pusta, ponieważ logika opuszczania mapy została przeniesiona do manage_crossings
        pass

    def determine_signal_strength(self):
        pass  # Opcjonalne

    def update_gps_coordinates(self):
        for tourist in self.simulation.tourists_dict.values():
            timestamp = self.simulation.sim_time.strftime("%Y-%m-%d %H:%M:%S.%f")
            if tourist.gps_enabled:
                loc = tourist.create_location(
                    longitude=tourist.last_location[0],
                    latitude=tourist.last_location[1],
                    loc_type="GPS",
                    timestamp=timestamp
                )

    def update_nearest_detector(self, tourists):
        pass  # Wymaga detektorów w map_sample.json

    def start_updating_animal_locations(self, delta):
        # --- faza 1: zbieramy wszystkie dane ---
        animal_locations = []
        location_records = []
        animal_loc_records = []

        # Jeśli zapis do bazy jest włączony, inicjalizujemy id_counter
        if self.simulation.save_to_db:
            id_counter = simulation_db.get_first_index_of_location(self.simulation.db)

        for animal_id in self.simulation.animal_ids:
            current = get_location_from_route(
                self.simulation.animal_routes[animal_id],
                self.simulation.sim_time
            )
            new_lon = current["longitude"] + random.uniform(-1.0, 1.0)
            new_lat = current["latitude"] + random.uniform(-1.0, 1.0)
            timestamp = self.simulation.sim_time.strftime("%Y-%m-%d %H:%M:%S.%f")

            # Przygotowujemy słownik do pliku JSON bez danych związanych z bazą
            loc = {
                "animal_id": animal_id,
                "longitude": new_lon,
                "latitude": new_lat,
                "simulated_timestamp": timestamp
            }
            animal_locations.append(loc)

            # Jeśli zapis do bazy jest włączony, przygotowujemy rekordy do tabel
            if self.simulation.save_to_db:
                # Dla tabeli location potrzebujemy location_id, longitude, latitude
                location_records.append((id_counter, new_lon, new_lat))
                # Dla tabeli animal_location potrzebujemy location_id, animal_id, simulation_id, timestamp
                simulation_id = self.simulation.next_id
                animal_loc_records.append((
                    id_counter,
                    animal_id,
                    simulation_id,
                    timestamp
                ))
                id_counter += 1

        # Zapisujemy lokalizacje do pliku JSON (bez danych związanych z bazą)
        with open("animal_locations.json", "w", encoding="utf-8") as f:
            json.dump(animal_locations, f, indent=4)

        # Jeśli zapis do bazy jest włączony, wykonujemy wstawianie danych
        if self.simulation.save_to_db:
            insert_loc_sql = """
                INSERT INTO simulation_gopr.location
                    (location_id, longitude, latitude)
                VALUES (%s, %s, %s);
            """
            self.simulation.db.execute_query(insert_loc_sql, location_records)

            insert_animal_loc_sql = """
                INSERT INTO simulation_gopr.animal_location
                    (location_id, animal_id, simulation_id, simulated_timestamp)
                VALUES (%s, %s, %s, %s);
            """
            self.simulation.db.execute_query(insert_animal_loc_sql, animal_loc_records)

