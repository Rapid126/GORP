import math
from datetime import datetime
import random

import simulation


class Tourist:
    ALLOWED_LOC_TYPES = ["BTS", "GPS"]

    def __init__(self, phone_id, route_number=None):
        self.phone_id = phone_id
        self.start_route_number = route_number  # Numer początkowej trasy
        self.current_route_number = route_number  # Aktualna trasa
        self.current_point_index = 0  # Indeks aktualnego punktu na trasie
        self.direction = 1  # 1: w przód, -1: w tył
        self.last_location = [0, 0]  # [longitude, latitude]
        self.is_moving = True  # Czy turysta się porusza
        self.is_lost = False  # Czy turysta będzie zbaczał z trasy
        self.is_out_of_route = False  # Czy turysta jest poza trasą
        self.outer_point = None  # Punkt docelowy, jeśli zgubiony
        self.gps_enabled = random.choice([True, False])  # Czy GPS jest włączony
        self.detector = None  # Aktualny detektor
        self.stats = {
            "entry_time": datetime.now(),
            "exit_time": None,
            "exit_type": None
        }
        self.weather_label = random.randint(1, 4)  # Etykieta pogodowa (1-4)
        self.last_timestamp = None
        self.base_speed = random.uniform(0.5, 2.0)
        self.current_speed = self.base_speed

    def create_location(self, longitude, latitude, loc_type="BTS", timestamp=None):
        if loc_type not in self.ALLOWED_LOC_TYPES:
            raise ValueError(f"Invalid loc_type. Allowed values are {self.ALLOWED_LOC_TYPES}")

        location = {
            "title": "touristLocation",
            "PhoneId": self.phone_id,
            "locType": loc_type,
            "timeStamp": timestamp,
            "location": {
                "longitude": str(longitude),
                "latitude": str(latitude)
            }
        }

        self.last_location = [longitude, latitude]
        return location

    def get_last_location(self):
        return self.last_location

    def set_coordinates(self, longitude, latitude, route_number, point_index):
        self.last_location = [longitude, latitude]
        self.current_route_number = route_number
        self.current_point_index = point_index

    def set_moving(self, is_moving):
        self.is_moving = is_moving

    def update_speed(self):
        chance = 0.1
        if random.random() < chance:
            variation = random.uniform(-0.1, 0.1)
            new_speed = self.base_speed + variation
            self.current_speed = max(0.5, min(2.0, new_speed))

    def set_out_of_route(self, is_out):
        self.is_out_of_route = is_out

    def set_outer_point(self, longitude, latitude):
        self.outer_point = [longitude, latitude]

    def set_detector(self, detector):
        self.detector = detector

    def set_direction(self, direction):
        self.direction = direction

    def should_get_injured(self):
        if random.randint(1, 1000) == 1:  # 1/1000 szansy
            self.is_moving = False  # Turysta przestaje się ruszać
            print(f"Turysta {self.phone_id} doznał kontuzji i przestał się poruszać.")

            self.maybe_start_moving_again()

    def should_get_lost_or_find_way(self):
        if self.is_lost:
            if random.randint(1, 100) == 1:  # 1/100 szansy
                self.is_lost = False
                print(f"Turysta {self.phone_id} znalazł drogę.")
        else:
            if random.randint(1, 500) == 1:  # 1/100 szansy
                self.is_lost = True
                print(f"Turysta {self.phone_id} zgubił drogę.")

    def check_special_places(self, special_places):
        for place in special_places:
            place_longitude = place["coordinates"]["longitude"]
            place_latitude = place["coordinates"]["latitude"]
            radius = place["radius"]

            distance = math.sqrt(
                (self.last_location[0] - place_longitude) ** 2 +
                (self.last_location[1] - place_latitude) ** 2
            )

            if distance <= radius:
                # 1/100 chance to stop moving
                if self.is_moving and random.randint(1, 10) == 1:
                    self.is_moving = False
                    print(f"Tourist {self.phone_id} stopped moving in the radius of a special place.")
                self.maybe_start_moving_again()
                return

    def maybe_start_moving_again(self):
        # 1/100 chance to start moving again
        if not self.is_moving and random.randint(1, 10) == 1:
            self.is_moving = True
            print(f"Tourist {self.phone_id} started moving again.")

    def insert_tourist_into_database(self,sim_id,simdb):
        if self.gps_enabled:
            loctype="GPS"
        else:
            loctype="BTS"

        upsert_tourist_sql = """
                                    INSERT INTO simulation_gopr.tourist(phone_id, location_type)
                                    VALUES (%s, %s)
                                    ON CONFLICT (phone_id) DO NOTHING;
                                """
        simdb.execute_query(upsert_tourist_sql, (self.phone_id, loctype), fetch=False)

        insert_sim_tourist_sql = """
                                    INSERT INTO simulation_gopr.simulated_tourist(phone_id, simulation_id)
                                    VALUES (%s, %s);
                                """

        simdb.execute_query(insert_sim_tourist_sql, (self.phone_id,sim_id), fetch=False)