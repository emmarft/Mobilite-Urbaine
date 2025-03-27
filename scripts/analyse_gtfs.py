import pandas as pd
import os
import folium
import matplotlib.pyplot as plt
import seaborn as sns
from folium.plugins import HeatMap

# Définir les chemins
boroughs = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten-Island"]
base_path = "../boroughs/"
result_path = "../resultats/"
viz_path = "../visualisation/"

# Vérifier et créer les dossiers de sortie
os.makedirs(result_path, exist_ok=True)
os.makedirs(viz_path, exist_ok=True)

for borough in boroughs:
    print(f"\n Traitement des données pour {borough}...\n")

    data_path = os.path.join(base_path, borough)
    borough_result_path = os.path.join(result_path, borough)
    borough_viz_path = os.path.join(viz_path, borough)

    os.makedirs(borough_result_path, exist_ok=True)
    os.makedirs(borough_viz_path, exist_ok=True)

    # Vérifier si tous les fichiers nécessaires sont présents
    files = ["stops.txt", "stop_times.txt", "trips.txt", "routes.txt", "calendar.txt", "shapes.txt", "calendar_dates.txt", "agency.txt"]
    missing_files = [file for file in files if not os.path.exists(os.path.join(data_path, file))]
    if missing_files:
        print(f"⚠️ Fichiers manquants pour {borough} : {missing_files}")
        continue

    # Charger les fichiers GTFS
    def load_csv(filename):
        return pd.read_csv(os.path.join(data_path, filename))

    stops = load_csv("stops.txt")
    stop_times = load_csv("stop_times.txt")
    trips = load_csv("trips.txt")
    routes = load_csv("routes.txt")
    calendar = load_csv("calendar.txt")
    shapes = load_csv("shapes.txt")
    calendar_dates = load_csv("calendar_dates.txt")
    agency = load_csv("agency.txt")

    print(f"Données chargées pour {borough} !")

    # Nettoyage et transformation des données
    stop_times["arrival_time"] = stop_times["arrival_time"].astype(str)
    stop_times["arrival_time"] = stop_times["arrival_time"].apply(lambda x:
        f"{int(x.split(':')[0]) - 24:02}:{x.split(':')[1]}:{x.split(':')[2]}" if int(x.split(':')[0]) >= 24 else x
    )
    stop_times["arrival_time"] = pd.to_datetime(stop_times["arrival_time"], format="%H:%M:%S", errors='coerce')
    stop_times["hour"] = stop_times["arrival_time"].dt.hour
    stop_times["minute"] = stop_times["arrival_time"].dt.minute
    stop_times["day"] = stop_times["arrival_time"].dt.dayofweek

    # Calcul des KPI
    total_stops = stops.shape[0]
    total_routes = routes.shape[0]
    total_trips = trips.shape[0]
    rush_hour_counts = stop_times["hour"].value_counts().sort_index()
    peak_hour = rush_hour_counts.idxmax() if not rush_hour_counts.empty else "N/A"

    print(f"KPI pour {borough}:")
    print(f"Total arrêts: {total_stops}, Total lignes: {total_routes}, Total trajets: {total_trips}, Heure de pointe: {peak_hour}")

    # Analyse de la fréquentation par heure
    plt.figure(figsize=(10, 5))
    plt.bar(rush_hour_counts.index, rush_hour_counts.values, color="skyblue")
    plt.xlabel("Heure de la journée")
    plt.ylabel("Nombre de passages")
    plt.title(f"Fréquentation des transports publics par heure - {borough}")
    plt.xticks(range(24))
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.savefig(os.path.join(borough_result_path, "frequentation_par_heure.png"))
    plt.close()

    # Carte des arrêts les plus fréquentés
    top_stops = stop_times["stop_id"].value_counts().index
    stops_filtered = stops[stops["stop_id"].isin(top_stops)]

    m = folium.Map(location=[40.7128, -74.0060], zoom_start=12)
    for _, row in stops_filtered.iterrows():
        folium.CircleMarker(
            location=[row["stop_lat"], row["stop_lon"]],
            radius=5, color="red", fill=True, fill_opacity=0.6,
            popup=f"Station: {row['stop_name']}\nFréquence: {stop_times['stop_id'].value_counts()[row['stop_id']]}",
        ).add_to(m)
    m.save(os.path.join(borough_viz_path, "carte_stations.html"))

    # Analyse des lignes les plus fréquentées
    top_routes = trips["route_id"].value_counts()
    plt.figure(figsize=(10, 5))
    top_routes.plot(kind="bar", color="orange")
    plt.xlabel("ID de la ligne")
    plt.ylabel("Nombre de trajets")
    plt.title(f"Lignes de transport les plus fréquentées - {borough}")
    plt.xticks(rotation=45)
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.savefig(os.path.join(borough_result_path, "lignes_populaires.png"))
    plt.close()

    # Heatmap de fréquentation par jour et heure
    heatmap_data = stop_times.groupby(["day", "hour"]).size().unstack()

    plt.figure(figsize=(12, 6))
    sns.heatmap(heatmap_data, cmap="coolwarm", annot=True, fmt="d")
    plt.xlabel("Heure de la journée")
    plt.ylabel("Jour de la semaine")
    plt.title(f"Fréquentation des transports par jour et heure - {borough}")
    plt.yticks(ticks=range(7), labels=["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"])
    plt.savefig(os.path.join(borough_result_path, "heatmap_frequentation.png"))
    plt.close()

    # Carte heatmap des zones de forte affluence
    heat_data = [[row["stop_lat"], row["stop_lon"]] for _, row in stops_filtered.iterrows()]
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=12)
    HeatMap(heat_data).add_to(m)
    m.save(os.path.join(borough_viz_path, "heatmap_stations.html"))

    print(f"Fichiers générés pour {borough} !")

    # Graphique des itinéraires les plus longs
    shapes['distance'] = ((shapes['shape_pt_lat'].diff()**2 + shapes['shape_pt_lon'].diff()**2)**0.5).cumsum()
    longest_routes = shapes.groupby('shape_id')['distance'].max().sort_values(ascending=False)
    plt.figure(figsize=(10, 5))
    longest_routes[:10].plot(kind='bar', color='purple')
    plt.xlabel("ID de l'itinéraire")
    plt.ylabel("Distance totale (approx)")
    plt.title(f"Longueur des itinéraires - {borough}")
    plt.savefig(os.path.join(borough_result_path, "itineraire_longueur.png"))
    plt.close()

     # Carte des itinéraires
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=12)
    colors = ["#FF6347", "#4682B4", "#32CD32", "#FFD700", "#8A2BE2", "#FF4500", "#2E8B57", "#D2691E", "#00008B", "#B8860B"]
    for i, (shape_id, group) in enumerate(shapes.groupby("shape_id")):
        points = list(zip(group["shape_pt_lat"], group["shape_pt_lon"]))
        color = colors[i % len(colors)]  
        folium.PolyLine(points, color=color, weight=2.5, opacity=0.7).add_to(m)
    m.save(os.path.join(borough_viz_path, "carte_itineraires.html"))

    # Analyse des jours exceptionnels
    exception_counts = calendar_dates["exception_type"].value_counts()
    plt.figure(figsize=(6,6))
    exception_counts.plot(kind="bar", color=["green", "red"])
    plt.xlabel("Type d'exception")
    plt.ylabel("Nombre de jours impactés")
    plt.xticks(ticks=[1, 2], labels=["Ajouté", "Supprimé"], rotation=0)
    plt.title(f"Jours de service exceptionnels - {borough}")
    plt.savefig(os.path.join(borough_result_path, "jours_exceptionnels.png"))
    plt.close()

    # Calcul des temps de trajet approximatifs (exemple simplifié)
    if not shapes.empty and not stop_times.empty:
        # Filtrer les données shapes
        shapes_filtered = shapes.sample(frac=0.1, random_state=42)

        # Filtrer et trier les données stop_times
        stop_times_filtered = stop_times.sort_values(by=["trip_id", "arrival_time"]).sample(frac=0.2, random_state=42)

        merged_data = pd.merge(stop_times_filtered, trips, on="trip_id")
        merged_data = pd.merge(merged_data, shapes_filtered, on="shape_id")

        # Calcul des différences de temps avec vérification des valeurs négatives
        merged_data["travel_time"] = merged_data.groupby("trip_id")["arrival_time"].diff().dt.total_seconds() / 60
        merged_data["travel_time"] = merged_data["travel_time"].apply(lambda x: abs(x) if x < 0 else x)  # Valeurs absolues

        average_travel_times = merged_data.groupby("route_id")["travel_time"].mean()
        plt.figure(figsize=(10, 5))
        average_travel_times.plot(kind="bar", color="skyblue")
        plt.xlabel("ID de la ligne")
        plt.ylabel("Temps de trajet moyen (minutes)")
        plt.title(f"Temps de trajet moyen par ligne - {borough}")
        plt.savefig(os.path.join(borough_result_path, "temps_trajet_moyen.png"))
        plt.close()

    # Graphique de comparaison des arrondissements
    if borough == "Manhattan": # On effectue la comparaison une seule fois
        borough_data = {}
        for b in boroughs:
            data_path_b = os.path.join(base_path, b)
            stop_times_b = pd.read_csv(os.path.join(data_path_b, "stop_times.txt"))
            stop_times_b["arrival_time"] = stop_times_b["arrival_time"].astype(str)
            stop_times_b["arrival_time"] = stop_times_b["arrival_time"].apply(lambda x: 
                f"{int(x.split(':')[0]) - 24:02}:{x.split(':')[1]}:{x.split(':')[2]}" if int(x.split(':')[0]) >= 24 else x
            )
            stop_times_b["arrival_time"] = pd.to_datetime(stop_times_b["arrival_time"], format="%H:%M:%S", errors='coerce')
            stop_times_b["hour"] = stop_times_b["arrival_time"].dt.hour
            borough_data[b] = stop_times_b["hour"].value_counts().sort_index()

        plt.figure(figsize=(12, 6))
        for b, data in borough_data.items():
            plt.plot(data.index, data.values, label=b)
        plt.xlabel("Heure de la journée")
        plt.ylabel("Nombre de passages")
        plt.title("Comparaison des fréquences par arrondissement")
        plt.xticks(range(24))
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        plt.savefig(os.path.join(result_path, "comparaison_arrondissements.png"))
        plt.close()

    print(f"Nouveaux graphiques et cartes générés pour {borough} !")
