from fastapi import FastAPI
from sqladmin import Admin, ModelView
from database import create_db_and_tables, engine, WifiDetection, WifiDevice, UplinkFrame
from routers import ttn, frontend, admin, algo
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


# --- ROUTERS (API & Pages Web) ---
# Page d'accueil (Tableau public) et Page Admin (Validation GPS)
app.include_router(frontend.router)

# Réception des données de l'ESP32
app.include_router(algo.router, prefix="/algo", tags=["Algo"])

# Ancienne route TTN (au cas où)
app.include_router(ttn.router, prefix="/ttn", tags=["TTN"])

# API pour les actions d'administration (ex: bouton "Valider GPS")
app.include_router(admin.router, prefix="/admin", tags=["Admin API"])


# --- INTERFACE VISUELLE BDD (SQLAdmin) ---
# Accessible via http://IP:PORT/db
# On configure base_url="/db" pour ne pas toucher au prefixe /admin de l'API

class WifiDeviceAdmin(ModelView, model=WifiDevice):
    name = "Point WiFi"
    name_plural = "Points WiFi"
    icon = "fa-solid fa-wifi"
    column_list = [
        WifiDevice.id, 
        WifiDevice.bssid, 
        WifiDevice.lat_estimated, 
        WifiDevice.lon_estimated, 
        WifiDevice.last_calculated_at
    ]

class UplinkFrameAdmin(ModelView, model=UplinkFrame):
    name = "Trame Reçue"
    name_plural = "Trames Reçues"
    icon = "fa-solid fa-satellite-dish"
    column_list = [
        UplinkFrame.id, 
        UplinkFrame.created_at, 
        UplinkFrame.lat_gps, 
        UplinkFrame.lat_estimated
    ]

class WifiDetectionAdmin(ModelView, model=WifiDetection):
    name = "Détection"
    name_plural = "Détections (Raw)"
    column_list = [WifiDetection.frame_id, WifiDetection.wifi_id, WifiDetection.rssi]

# Initialisation sur /db
admin_interface = Admin(app, engine, base_url="/db", title="DB Admin")
admin_interface.add_view(WifiDeviceAdmin)
admin_interface.add_view(UplinkFrameAdmin)
admin_interface.add_view(WifiDetectionAdmin)
