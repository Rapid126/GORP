import json
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from datetime import datetime

import simulation_db
from weather_events import add_weather_event
from simulation import Simulation

CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "animals": [
                {"type": "jeleń",
                 "route_number": 2,
                 "start_longitude": None,
                 "start_latitude": None}
            ],
              "time_multiplier": 60,
              "start_time": "2025-04-06 08:00:00",
              "duration_hours": 5
        }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def load_paths():
    try:
        with open("map_sample.json", "r") as f:
            data = json.load(f)
            return data.get("routes", [])
    except FileNotFoundError:
        messagebox.showerror("Błąd", "Nie znaleziono pliku map_sample.json")
        return []
    except json.JSONDecodeError:
        messagebox.showerror("Błąd", "Plik map_sample.json zawiera nieprawidłowy JSON")
        return []

def save_paths(paths):
    try:
        with open("map_sample.json", "r") as f:
            data = json.load(f)
        data["routes"] = paths  # Uaktualniamy listę routes
        with open("map_sample.json", "w") as f:
            json.dump(data, f, indent=2)  # Zapisujemy zaktualizowane dane w pliku
    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się zapisać zmian: {e}")

def main():
    with open("map_sample.json", "r", encoding="utf-8") as f:
        map_sample = json.load(f)
    ROUTE_NUMBERS = [0] + [route["number"] for route in map_sample["routes"]]

    config = load_config()
    paths = load_paths()
    sim = Simulation()

    def get_simulation_duration():
        config = load_config()
        return config["duration_hours"] * 60

    def is_valid_event_time(minute):
        max_time_in_minutes = get_simulation_duration()
        return 0 <= minute < max_time_in_minutes

    def start_simulation():
        if save_to_db_var.get():
            if not sim.db.connection:
                sim.db.connect()
                sim.next_id = simulation_db.get_first_index(sim.db)
        sim.save_to_db = save_to_db_var.get()
        sim.start()
        update_progress_bar()

    def stop_simulation():
        sim.stop()

    def reset_simulation():
        sim.reset()
        progress_var.set(0)

    def update_progress_bar():
        if sim.is_running:
            elapsed = sim.get_elapsed_time()
            total = sim.get_total_duration()
            progress = min(100, (elapsed / total) * 100)
            progress_var.set(progress)
            root.after(1000, update_progress_bar)

    def save_config_from_entries():
        try:
            new_config = {
                "time_multiplier": int(multiplier_entry.get()),
                "start_time": start_time_entry.get(),
                "duration_hours": int(duration_entry.get()),
            }
            # walidujemy format czasu
            datetime.strptime(new_config["start_time"], "%Y-%m-%d %H:%M:%S")
            save_config(new_config)
            messagebox.showinfo("Sukces", "Konfiguracja została zapisana.")
        except ValueError as e:
            messagebox.showerror("Błąd", f"Nieprawidłowe dane: {e}")
        reset_simulation()

    root = tk.Tk()
    root.title("Symulacja")
    root.geometry("500x600")

    notebook = ttk.Notebook(root)
    frame_sim = tk.Frame(notebook)
    frame_tourist = tk.Frame(notebook)
    frame_weather = tk.Frame(notebook)
    frame_animals = tk.Frame(notebook)
    notebook.add(frame_sim, text="Symulacja")
    notebook.add(frame_weather, text="Pogoda")
    notebook.add(frame_tourist, text="Turysci")
    notebook.add(frame_animals, text="Zwierzeta")
    notebook.pack(expand=True, fill="both")

    def add_labeled_entry(master, label_text, default_value):
        frame = tk.Frame(master)
        frame.pack(pady=2)
        tk.Label(frame, text=label_text, width=25, anchor="w").pack(side="left")
        entry = tk.Entry(frame, width=25)
        entry.insert(0, str(default_value))
        entry.pack(side="right")
        return entry

    start_time_entry = add_labeled_entry(frame_sim, "Czas startu:", config["start_time"])
    duration_entry = add_labeled_entry(frame_sim, "Czas trwania (h):", config["duration_hours"])

    save_to_db_var = tk.BooleanVar(value=False)
    tk.Checkbutton(frame_sim, text="Zapis do bazy danych", variable=save_to_db_var).pack(pady=5)

    tk.Button(frame_sim, text="Zapisz konfigurację", command=save_config_from_entries).pack(pady=10)

    multiplier_dynamic_frame = tk.Frame(frame_sim)
    multiplier_dynamic_frame.pack(pady=10)

    tk.Label(multiplier_dynamic_frame, text="Mnożnik czasu (dynamicznie):", width=25, anchor="w").pack(side="left")
    multiplier_entry = tk.Entry(multiplier_dynamic_frame, width=10)
    multiplier_entry.insert(0, str(config["time_multiplier"]))
    multiplier_entry.pack(side="left", padx=5)

    def update_multiplier():
        try:
            new_multiplier = int(multiplier_entry.get())
            sim.set_time_multiplier(new_multiplier)
            config = load_config()
            config["time_multiplier"] = new_multiplier
            save_config(config)
            messagebox.showinfo("Sukces", f"Mnożnik czasu zmieniony i zapisany: {new_multiplier}")
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowa wartość mnożnika")

    tk.Button(multiplier_dynamic_frame, text="Zmień", command=update_multiplier).pack(side="left")

    # === Sekcja Pogoda ===
    fields = {}
    for field in ["Minuta", "Detektory (np. 1,2,3)", "Temperatura", "Wiatr", "Mgła", "Deszcz"]:
        row = tk.Frame(frame_weather)
        row.pack(pady=2)
        label = tk.Label(row, text=field + ":", width=25, anchor="w")
        label.pack(side="left")
        entry = tk.Entry(row, width=15)
        entry.pack(side="right")
        fields[field] = entry

    def set_weather_values(kind):
        values = {"Temperatura": 20, "Wiatr": 5, "Mgła": 0, "Deszcz": 0} if kind == "good" else {"Temperatura": -10, "Wiatr": 90, "Mgła": 9, "Deszcz": 95}
        for k, v in values.items():
            fields[k].delete(0, tk.END)
            fields[k].insert(0, str(v))

    # === Lista zdarzeń pogodowych ===
    event_list_frame = tk.Frame(frame_weather)
    event_list_frame.pack(fill="both", expand=True, pady=10)

    def load_weather_events():
        try:
            with open("weather_events.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def delete_weather_event(index):
        events = load_weather_events()
        if index < len(events):
            events.pop(index)
            with open("weather_events.json", "w") as f:
                json.dump(events, f, indent=2)
            refresh_event_list()

    def refresh_event_list():
        for widget in event_list_frame.winfo_children():
            widget.destroy()

        events = load_weather_events()
        for idx, event in enumerate(events):
            desc = f"Min: {event['minute']} | Detektor: {event['detectorNumber']} | Temperatura: {event['temperature']} | Wiatr: {event['wind']} | Mgła: {event['fog']} | Deszcz: {event['rain']}"
            row = tk.Frame(event_list_frame)
            row.pack(fill="x", pady=2, padx=5)
            label = tk.Label(row, text=desc, anchor="w", justify="left")
            label.pack(side="left", fill="x", expand=True)
            delete_btn = tk.Button(row, text="X", fg="red", command=lambda i=idx: delete_weather_event(i))
            delete_btn.pack(side="right")

    def submit_weather_event():
        try:
            minute = int(fields["Minuta"].get())
            if not is_valid_event_time(minute):
                messagebox.showerror("Błąd", "Minuta zdarzenia przekracza czas trwania symulacji.")
                return
            add_weather_event(
                minute,
                fields["Detektory (np. 1,2,3)"].get(),
                float(fields["Temperatura"].get()),
                float(fields["Wiatr"].get()),
                float(fields["Mgła"].get()),
                float(fields["Deszcz"].get())
            )
            messagebox.showinfo("OK", "Zdarzenie pogodowe zapisane")
            refresh_event_list()
        except ValueError as e:
            messagebox.showerror("Błąd", f"{e}")

    btn_row = tk.Frame(frame_weather)
    btn_row.pack(pady=5)
    tk.Button(btn_row, text="Ładna pogoda", command=lambda: set_weather_values("good")).pack(side="left", padx=5)
    tk.Button(btn_row, text="Brzydka pogoda", command=lambda: set_weather_values("bad")).pack(side="left", padx=5)
    tk.Button(frame_weather, text="Dodaj zdarzenie", command=submit_weather_event).pack(pady=5)

    refresh_event_list()

    # === Sekcja Turysta ===

    # Dodanie napisu "Natężenie na ścieżkach" przed polami edycyjnymi
    intensity_label = tk.Label(frame_tourist, text="Natężenie na ścieżkach", font=("Arial", 14, "bold"))
    intensity_label.pack(pady=10)

    path_list_frame = tk.Frame(frame_tourist)
    path_list_frame.pack(fill="both", expand=True, pady=10)



    def refresh_path_list():
        for widget in path_list_frame.winfo_children():
            widget.destroy()

        # Filtrowanie ścieżek, aby zostawić tylko te, które mają isEntrance = True
        valid_paths = [path for path in paths if path.get("isEntrance")]

        for path in valid_paths:
            row = tk.Frame(path_list_frame)
            row.pack(fill="x", pady=2, padx=5)

            # Wyświetlanie ID ścieżki
            tk.Label(row, text=f"ID: {path['number']}", anchor="w").pack(side="left", padx=5)

            # Wartość spawnChance
            spawn_chance_var = tk.DoubleVar(
                value=path.get("spawn_chance", 0.0))  # Używamy get(), by zapewnić domyślną wartość 0.0
            spawn_chance_entry = tk.Entry(row, textvariable=spawn_chance_var, width=10)
            spawn_chance_entry.pack(side="left", padx=5)

            # Funkcja do zapisywania zmian w spawnChance
            def save_path_state(p=path, var=spawn_chance_var):
                try:
                    p["spawn_chance"] = float(var.get())  # Zmieniamy spawnChance na nową wartość
                    save_paths(paths)  # Zapisujemy ścieżki do pliku
                    messagebox.showinfo("Sukces", f"Zmieniono spawnChance dla ścieżki {p['number']}")
                except ValueError:
                    messagebox.showerror("Błąd", "Nieprawidłowa wartość szansy na spawn")

            # Przycisk zapisu
            tk.Button(row, text="Zapisz", command=save_path_state).pack(side="left", padx=5)

    tk.Button(frame_tourist, text="Odśwież listę ścieżek", command=refresh_path_list).pack(pady=5)

    refresh_path_list()

    # ===sekcja Zwierzeta===
    ANIMAL_OPTIONS=["jelen","sarna","lis","wilk","niedzwiedz"]
    animal_list = config.get("animals", [])

    def save_animals():
        animals = []
        try:
            for row in animal_list_frame.winfo_children():
                if not hasattr(row, "type_var") or not hasattr(row, "start_lon_entry") or not hasattr(row,"start_lat_entry"):
                    continue
                lon = row.start_lon_entry.get().strip()
                lat = row.start_lat_entry.get().strip()
                animals.append({
                    "type": row.type_var.get(),
                    "route_number": row.route_var.get(),
                    "start_longitude": float(lon) if lon else None,
                    "start_latitude": float(lat) if lat else None,
                })
            config["animals"] = animals
            config["num_animals"] = len(animals)
            save_config(config)
            messagebox.showinfo("Sukces", "Zwierzęta zapisane.")
            reset_simulation()
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def add_animal_row(default_type="jelen",
                       default_route=0,
                       default_lon=None,
                       default_lat=None):
        row = tk.Frame(animal_list_frame)
        row.pack(pady=2, fill="x")

        # --- typ zwierzęcia ---
        type_var = tk.StringVar(value=default_type)
        ttk.Combobox(row, textvariable=type_var,
                     values=ANIMAL_OPTIONS, state="readonly", width=12) \
            .pack(side="left", padx=5)

        # --- start long / lat ---
        start_lon_entry = tk.Entry(row, width=8);
        start_lon_entry.pack(side="left", padx=5)
        if default_lon is not None: start_lon_entry.insert(0, str(default_lon))

        start_lat_entry = tk.Entry(row, width=8);
        start_lat_entry.pack(side="left", padx=5)
        if default_lat is not None: start_lat_entry.insert(0, str(default_lat))

        # --- wybór trasy (0 = żadna) ---
        route_var = tk.IntVar(value=default_route)
        ttk.Combobox(row, textvariable=route_var,
                     values=ROUTE_NUMBERS, state="readonly", width=5) \
            .pack(side="left", padx=5)

        # przechowanie var jako atrybut wiersza
        row.type_var = type_var
        row.route_var = route_var
        row.start_lon_entry = start_lon_entry
        row.start_lat_entry = start_lat_entry

        tk.Button(row, text="Usuń", fg="red", command=row.destroy) \
            .pack(side="right", padx=5)

    animal_list_frame = tk.Frame(frame_animals)
    animal_list_frame.pack(pady=10, fill="x")

    animal_list_frame = tk.Frame(frame_animals)
    animal_list_frame.pack(pady=10, fill="x")

    # +++ HEADER: opisy kolumn +++
    header = tk.Frame(animal_list_frame)
    header.pack(fill="x", padx=5)

    tk.Label(header, text="Typ", width=10, anchor="w").pack(side="left", padx=5)
    tk.Label(header, text="Start Long.", width=8, anchor="w").pack(side="left", padx=5)
    tk.Label(header, text="Start Lat.", width=8, anchor="w").pack(side="left", padx=5)
    tk.Label(header, text="Trasa(przez którą zwierze ma przejsc)",  anchor="w").pack(side="left", padx=5)
    tk.Label(header, text="Akcje", width=6, anchor="w").pack(side="right", padx=5)

    # Załadowanie istniejące zwierzęta
    for animal in animal_list:
        add_animal_row(
            default_type=animal["type"],
            default_lon=animal.get("start_longitude"),
            default_lat=animal.get("start_latitude"),
            default_route=animal.get("route_number")
        )

    tk.Button(frame_animals, text="Dodaj zwierzę", command=add_animal_row).pack(pady=5)
    tk.Button(frame_animals, text="Zapisz zwierzęta", command=save_animals).pack(pady=5)

    style = ttk.Style()
    style.theme_use('default')
    style.configure("blue.Horizontal.TProgressbar", troughcolor='white', background='blue')

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, style="blue.Horizontal.TProgressbar")
    progress_bar.pack(pady=10, fill="x", padx=10)

    start_stop_frame = tk.Frame(root)
    start_stop_frame.pack(pady=5)
    start_btn = tk.Button(start_stop_frame, text="Start", command=start_simulation, width=10, height=2)
    start_btn.pack(side="left", padx=5)
    stop_btn = tk.Button(start_stop_frame, text="Stop", command=stop_simulation, width=10, height=2)
    stop_btn.pack(side="left", padx=5)
    reset_btn = tk.Button(root, text="Reset", command=reset_simulation, width=15, height=2)
    reset_btn.pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
