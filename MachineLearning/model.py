import sys
import os
import json
import numpy as np

# --- IMPORTS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(root_dir)

from Serveur.database import engine, UplinkFrame, WifiDevice
from sqlmodel import Session, select

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split

AUGMENTATION_FACTOR = 10
NOISE_LEVEL = 4.0
DEFAULT_RSSI = -100.0


def main():
    with Session(engine) as session:
        # Récupération des données
        frames = session.exec(select(UplinkFrame).where(UplinkFrame.lat_gps != None)).all()
        all_wifis = session.exec(select(WifiDevice)).all()

        if not frames:
            print("❌ Pas de données !")
            return

        print(f"✅ {len(frames)} points réels.")

        # --- 1. CALCUL DU CADRE (MIN/MAX) ---
        # On récupère tous les GPS pour trouver les bornes
        lats = [f.lat_gps for f in frames]
        lons = [f.lon_gps for f in frames]

        geo_limits = {
            "lat_min": min(lats),
            "lat_max": max(lats),
            "lon_min": min(lons),
            "lon_max": max(lons)
        }

        # Petite marge de sécurité pour ne pas être coincé aux bords
        margin = 0.001  # ~100m
        geo_limits["lat_min"] -= margin
        geo_limits["lat_max"] += margin
        geo_limits["lon_min"] -= margin
        geo_limits["lon_max"] += margin

        print(f"🌍 Zone de travail : Lat[{geo_limits['lat_min']:.4f}-{geo_limits['lat_max']:.4f}]")

        bssid_to_index = {w.bssid: i for i, w in enumerate(all_wifis)}
        num_features = len(all_wifis)

        X = []
        Y = []

        print("🛠️ Préparation et Normalisation...")

        for frame in frames:
            # Vecteur RSSI
            base_vector = np.full(num_features, DEFAULT_RSSI)
            for det in frame.detections:
                if det.wifi.bssid in bssid_to_index:
                    base_vector[bssid_to_index[det.wifi.bssid]] = det.rssi

            # Augmentation
            for i in range(AUGMENTATION_FACTOR):
                new_vector = base_vector.copy()
                if i > 0:
                    mask = new_vector > (DEFAULT_RSSI + 1)
                    noise = np.random.normal(0, NOISE_LEVEL, size=num_features)
                    new_vector[mask] += noise[mask]

                # Normalisation INPUT (RSSI) -> 0..1
                x_norm = (new_vector + 100) / 70.0
                x_norm = np.clip(x_norm, 0.0, 1.0)

                # --- 2. NORMALISATION OUTPUT (GPS) -> 0..1 ---
                # Formule : (Valeur - Min) / (Max - Min)
                lat_norm = (frame.lat_gps - geo_limits["lat_min"]) / (geo_limits["lat_max"] - geo_limits["lat_min"])
                lon_norm = (frame.lon_gps - geo_limits["lon_min"]) / (geo_limits["lon_max"] - geo_limits["lon_min"])

                X.append(x_norm)
                Y.append([lat_norm, lon_norm])

        X = np.array(X)
        Y = np.array(Y)

        # Entraînement
        X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

        model = keras.Sequential([
            layers.Input(shape=(num_features,)),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(32, activation='relu'),
            layers.Dense(2, activation='sigmoid')  # <--- Sigmoid force la sortie entre 0 et 1 !
        ])

        model.compile(optimizer='adam', loss='mse', metrics=['mae'])

        print("🚀 Entraînement...")
        model.fit(X_train, y_train, epochs=100, batch_size=16, validation_data=(X_test, y_test), verbose=1)

        # Sauvegarde
        print("💾 Sauvegarde...")
        model.save(os.path.join(current_dir, "wifi_model.keras"))

        # On sauvegarde aussi le mapping BSSID ET les limites GPS
        config = {
            "bssid_map": bssid_to_index,
            "geo_limits": geo_limits
        }
        with open(os.path.join(current_dir, "model_config.json"), "w") as f:
            json.dump(config, f)

        print("✅ Terminé. Configuration sauvegardée dans model_config.json")



        # --- 7. TEST FINAL (DÉNORMALISATION) ---
        print("\n" + "=" * 40)
        print("🎯 TEST DE VÉRIFICATION (3 points au hasard)")
        print("=" * 40)

        # On prend 3 points du set de TEST (ceux que le modèle n'a jamais vus)
        sample_indices = range(min(3, len(X_test)))
        predictions = model.predict(X_test[sample_indices])

        for i in sample_indices:
            pred_norm = predictions[i]
            true_norm = y_test[i]

            # Reconversion (0..1 -> GPS Réel)
            lat_pred = pred_norm[0] * (geo_limits["lat_max"] - geo_limits["lat_min"]) + geo_limits["lat_min"]
            lon_pred = pred_norm[1] * (geo_limits["lon_max"] - geo_limits["lon_min"]) + geo_limits["lon_min"]

            lat_true = true_norm[0] * (geo_limits["lat_max"] - geo_limits["lat_min"]) + geo_limits["lat_min"]
            lon_true = true_norm[1] * (geo_limits["lon_max"] - geo_limits["lon_min"]) + geo_limits["lon_min"]

            # Calcul erreur approximative (en degrés, *111km pour convertir en mètres à la louche)
            err_lat_m = abs(lat_pred - lat_true) * 111132
            err_lon_m = abs(lon_pred - lon_true) * 78710  # (dépend de la latitude, c'est une approx pour Paris)
            err_dist = (err_lat_m ** 2 + err_lon_m ** 2) **0.5

            print(f"📍 Point #{i + 1}")
            print(f"   Vrai   : {lat_true:.5f}, {lon_true:.5f}")
            print(f"   Prédit : {lat_pred:.5f}, {lon_pred:.5f}")
            print(f"   ⚠️ Erreur : ~{err_dist:.1f} mètres")
            print("-" * 20)


if __name__ == "__main__":
    main()