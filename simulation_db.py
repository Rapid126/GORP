
def get_first_index(db):
    sql = """
        WITH possible_ids AS (
            SELECT generate_series(1, (SELECT COALESCE(MAX(simulation_id),0) + 1 FROM simulation_gopr.simulation)) AS id
        )
        SELECT id
        FROM possible_ids p
        LEFT JOIN simulation_gopr.simulation s ON s.simulation_id = p.id
        WHERE s.simulation_id IS NULL
        ORDER BY p.id
        LIMIT 1;
    """
    return db.execute_query(sql, fetch=True)[0][0]

def get_first_index_of(db, searched, source):
    sql = f"""
        WITH possible_ids AS (
            SELECT generate_series(1, (SELECT COALESCE(MAX({searched}), 0) + 1 FROM simulation_gopr.{source})) AS id
        )
        SELECT id
        FROM possible_ids p
        LEFT JOIN simulation_gopr.{source} s ON s.{searched} = p.id
        WHERE s.{searched} IS NULL
        ORDER BY p.id
        LIMIT 1;
    """
    return db.execute_query(sql, fetch=True)[0][0]

def get_first_index_of_location(db):
    sql = """
        WITH possible_ids AS (
            SELECT generate_series(1, (SELECT COALESCE(MAX(location_id), 0) + 1 FROM simulation_gopr.location)) AS id
        )
        SELECT id
        FROM possible_ids p
        LEFT JOIN simulation_gopr.location l ON l.location_id = p.id
        WHERE l.location_id IS NULL
        ORDER BY p.id
        LIMIT 1;
    """
    return db.execute_query(sql, fetch=True)[0][0]

def check_map_conflict(db, map_name):
    sql = """
        SELECT m.map_name
        FROM simulation_gopr.map m
        WHERE m.map_name = %s
        LIMIT 1;
    """
    return bool(db.execute_query(sql, (map_name,), fetch=True))

def insert_map(db, map_name, canvas_width, canvas_height):
    sql = """
        INSERT INTO simulation_gopr.map
            (map_name, canvas_width, canvas_height, canvas_source_file, top_left_id, down_right_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (map_name)
        DO NOTHING;
    """
    db.execute_query(sql, (map_name, canvas_width, canvas_height, None, None, None), fetch=False)

def insert_special_place(db, place_id, radius, longitude, latitude):
    location_id = get_first_index_of_location(db)

    sql_insert_location = """
                    INSERT INTO simulation_gopr.location
                    (location_id, longitude, latitude)
                    VALUES (%s, %s, %s)
                """
    db.execute_query(sql_insert_location, (
        location_id,
        longitude,
        latitude
    ))

    sql = """
        INSERT INTO simulation_gopr.special_place
            (place_id, radius, location_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (place_id)
        DO NOTHING;
    """
    db.execute_query(sql, (place_id, radius, location_id), fetch=False)

def link_special_place_to_map(db, place_id, map_name, place_number):
    sql = """
        INSERT INTO simulation_gopr.special_place_map
            (place_id, map_name, place_number)
        VALUES (%s, %s, %s);
    """
    db.execute_query(sql, (place_id, map_name, place_number), fetch=False)



def insert_bts_station(db, station_id, longitude, latitude):
    location_id = get_first_index_of_location(db)

    sql_insert_location = """
                    INSERT INTO simulation_gopr.location
                    (location_id, longitude, latitude)
                    VALUES (%s, %s, %s)
                """
    db.execute_query(sql_insert_location, (
        location_id,
        longitude,
        latitude
    ))

    sql = """
        INSERT INTO simulation_gopr.bts_station
            (bts_station_id, location_id)
        VALUES (%s, %s)
        ON CONFLICT (bts_station_id)
        DO NOTHING;
    """
    db.execute_query(sql, (station_id, location_id), fetch=False)
    print("dodano stację")

def link_bts_station_to_map(db, station_id, map_name, station_number):
    sql = """
        INSERT INTO simulation_gopr.bts_station_map
            (station_id, map_name, station_number)
        VALUES (%s, %s, %s);
    """
    db.execute_query(sql, (station_id, map_name, station_number), fetch=False)
    print("polaczono stacje")



def insert_simulated_map(db, sim_id, map_name):
    sql = """
        INSERT INTO simulation_gopr.simulated_map
            (simulation_id, map_name)
        VALUES (%s, %s);
    """
    db.execute_query(sql, (sim_id, map_name), fetch=False)

def insert_simulation(db, sim_id, start_time_dt, set_duration_time, end_time_epoch):
    sql = """
        INSERT INTO simulation_gopr.simulation
            (simulation_id, start_time, set_duration, end_time)
        VALUES (%s, %s, %s, %s);
    """
    db.execute_query(sql, (sim_id, start_time_dt, set_duration_time, end_time_epoch), fetch=False)

def insert_animal(db, animal_id):
    sql = """
        INSERT INTO simulation_gopr.animal(animal_id)
        VALUES (%s)
        ON CONFLICT (animal_id) DO NOTHING;
    """
    db.execute_query(sql, (animal_id,), fetch=False)

def link_animal_to_simulation(db, animal_id, sim_id):
    sql = """
        INSERT INTO simulation_gopr.simulated_animal(animal_id, simulation_id)
        VALUES (%s, %s);
    """
    db.execute_query(sql, (animal_id, sim_id), fetch=False)

def check_weather_station_conflict(db, weather_station_id):
    sql = """
        SELECT m.weather_station_id
        FROM simulation_gopr.weather_station m
        WHERE m.weather_station_id = %s
        LIMIT 1;
    """
    return bool(db.execute_query(sql, (weather_station_id,), fetch=True))

def insert_weather_station(db, station):
    location_id = get_first_index_of_location(db)

    sql_insert_location = """
                        INSERT INTO simulation_gopr.location
                        (location_id, longitude, latitude)
                        VALUES (%s, %s, %s)
                    """
    db.execute_query(sql_insert_location, (
        location_id,
        station["location"]["longitude"],
        station["location"]["latitude"]
    ))

    sql = """
        INSERT INTO simulation_gopr.weather_station (
            weather_station_id, location_id
        ) VALUES (%s, %s);
    """
    params = (
        station["stationId"],
        location_id
    )
    db.execute_query(sql, params, fetch=False)

def link_weather_station_to_map(db, station, map_name):
    sql = """
        INSERT INTO simulation_gopr.weather_station_map
            (station_id, map_name, station_number)
        VALUES (%s, %s, %s);
    """
    db.execute_query(sql, (station["stationId"], map_name, None), fetch=False)

def insert_weather_record(db, station, sim_time, sim_id, reading_id):

    sql = """
        INSERT INTO simulation_gopr.weather_reading (
            reading_id, timestamp, wind, fog, temperature, rain, station_id, simulation_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    params = (
        reading_id,
        sim_time,
        station["wind"],
        station["fog"],
        station["temperature"],
        station["rain"],
        station["stationId"],
        sim_id
    )
    db.execute_query(sql, params, fetch=False)

def bulk_insert_tourist_locations(db, sim_id, tourists_j, location_id_counter):
    location_records = []
    tourist_loc_records = []

    for tourist in tourists_j:
        location_records.append((
            location_id_counter,
            float(tourist["location"]["longitude"]),
            float(tourist["location"]["latitude"])
        ))
        tourist_loc_records.append((
            tourist["PhoneId"],
            location_id_counter,
            tourist["timeStamp"],
            sim_id
        ))

        location_id_counter += 1

    db.execute_query("""
           INSERT INTO simulation_gopr.location
           (location_id, longitude, latitude)
           VALUES %s
       """, location_records, use_execute_values=True)

    db.execute_query("""
           INSERT INTO simulation_gopr.tourist_location
           (phone_id, location_id, simulated_timestamp, simulation_id)
           VALUES %s
       """, tourist_loc_records, use_execute_values=True)

    return location_id_counter

def insert_route_with_points(db, map_name, route_data):
    """
    Wstawia jedną trasę i wszystkie jej punkty (lokacje) do bazy danych jako jedną transakcję.
    """
    try:

        db.begin()

        route_id = get_first_index_of(db, "route_id", "route")

        sql_insert_route = """
            INSERT INTO simulation_gopr.route
            (route_id, route_number, difficulty, color, is_entrance, area, map_name)
            VALUES (%s, %s, %s, %s, %s, NULL, %s)
        """
        db.execute_query(sql_insert_route, (
            route_id,
            route_data["number"],
            route_data["difficulty"],
            route_data["color"].lower(),  # DB constraint expects lowercase
            route_data["isEntrance"],
            map_name
        ))

        for point in route_data["points"]:
            location_id = get_first_index_of_location(db)

            sql_insert_location = """
                INSERT INTO simulation_gopr.location
                (location_id, longitude, latitude)
                VALUES (%s, %s, %s)
            """
            db.execute_query(sql_insert_location, (
                location_id,
                point["longitude"],
                point["latitude"]
            ))

            sql_insert_route_point = """
                INSERT INTO simulation_gopr.route_point
                (route_id, location_id, point_number)
                VALUES (%s, %s, %s)
            """
            db.execute_query(sql_insert_route_point, (
                route_id,
                location_id,
                point["point"]
            ))

        db.commit()

    except Exception as e:

        db.rollback()
        raise Exception(f"Nie udało się dodać trasy: {e}")