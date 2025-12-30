import sys
import os
import json
import numpy as np
import sqlite3

# --- 1. CONFIGURATION DES CHEMINS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# On importe les configurations directement depuis votre projet
# pour être sûr d'utiliser le MÊME fichier .db que le serveur
from Serveur.database import engine, UplinkFrame, sqlite_file, WifiDevice
from sqlmodel import Session, select
import tensorflow as tf
from tensorflow import keras

# Chemins pour le modèle
ml_dir = os.path.join(current_dir, "MachineLearning")
model_path = os.path.join(ml_dir, "wifi_model.keras")
config_path = os.path.join(ml_dir, "model_config.json")

print(f"📂 Cible BDD : {sqlite_file}")

# --- 2. MIGRATION SQL (ROBUSTE) ---
print("🔧 Mise à jour de la structure de la BDD...")
conn = sqlite3.connect(sqlite_file)
cursor = conn.cursor()

# On essaie d'ajouter les colonnes une par une
columns_to_add = [
    ("lat_ml", "FLOAT"),
    ("lon_ml", "FLOAT")
]

for col_name, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE uplinkframe ADD COLUMN {col_name} {col_type}")
        print(f"   ✅ Colonne '{col_name}' ajoutée.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"   ℹ️ Colonne '{col_name}' déjà existante.")
        else:
            # Si c'est une autre erreur (ex: table introuvable), on l'affiche !
            print(f"   ❌ ERREUR CRITIQUE sur '{col_name}' : {e}")
            conn.close()
            sys.exit(1)

conn.commit()
conn.close()

# --- 3. CHARGEMENT DU MODÈLE ---
if not os.path.exists(model_path):
    print(f"❌ Modèle introuvable ici : {model_path}")
    print("👉 Avez-vous lancé 'MachineLearning/train_offline.py' ?")
    sys.exit(1)

print("🧠 Chargement du modèle IA...")
try:
    model = keras.models.load_model(model_path)
    with open(config_path, "r") as f:
        config = json.load(f)
        bssid_map = config["bssid_map"]
        geo = config["geo_limits"]
except Exception as e:
    print(f"❌ Erreur lors du chargement du modèle : {e}")
    sys.exit(1)

num_features = len(bssid_map)

# --- 4. CALCUL DES PRÉDICTIONS ---
print("🔄 Calcul des positions pour l'historique...")
with Session(engine) as session:
    # On prend toutes les trames qui n'ont pas encore de prédiction ML
    # OU toutes les trames pour forcer la mise à jour (plus sûr ici)
    frames = session.exec(select(UplinkFrame)).all()
    print(f"   -> {len(frames)} trames à traiter.")

    count = 0
    for frame in frames:
        # Préparation Vecteur
        vec = np.full(num_features, -100.0)
        has_signal = False

        for det in frame.detections:
            if det.wifi.bssid in bssid_map:
                vec[bssid_map[det.wifi.bssid]] = det.rssi
                has_signal = True

        if has_signal:
            # Normalisation (Doit être identique au training !)
            vec_norm = (vec + 100) / 70.0
            vec_norm = np.clip(vec_norm, 0.0, 1.0)

            # Prédiction
            # verbose=0 évite de spammer la console
            pred = model.predict(np.expand_dims(vec_norm, axis=0), verbose=0)[0]

            # Dénormalisation
            lat_final = pred[0] * (geo["lat_max"] - geo["lat_min"]) + geo["lat_min"]
            lon_final = pred[1] * (geo["lon_max"] - geo["lon_min"]) + geo["lon_min"]

            # Mise à jour
            frame.lat_ml = float(lat_final)
            frame.lon_ml = float(lon_final)
            session.add(frame)
            count += 1

            if count % 50 == 0:
                print(f"   ... {count} traités")

    session.commit()
    print(f"✅ Terminé ! {count} trames mises à jour avec l'IA.")