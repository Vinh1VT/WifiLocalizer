# main.py
from fastapi import FastAPI
from database import create_db_and_tables,engine, WifiDetection, WifiDevice,UplinkFrame
from routers import ttn,frontend,admin
from sqladmin import Admin,ModelView

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# C'est ici que la magie opère :
# On ajoute les routes du frontend (à la racine)
app.include_router(frontend.router)

# On ajoute les routes TTN (préfixées par /ttn pour être propre)
# L'URL finale sera donc : http://ton-domaine/ttn/webhook
app.include_router(ttn.router, prefix="/ttn", tags=["TTN"])

app.include_router(admin.router, prefix="/admin", tags=["Admin"])

class WifiDeviceAdmin(ModelView, model=WifiDevice):
    # Colonnes à afficher dans le tableau
    column_list = [WifiDevice.id, WifiDevice.bssid, WifiDevice.lat_estimated, WifiDevice.last_calculated_at]
    name = "Point WiFi"
    name_plural = "Points WiFi"

class UplinkFrameAdmin(ModelView, model=UplinkFrame):
    column_list = [UplinkFrame.id, UplinkFrame.created_at, UplinkFrame.lat_gps, UplinkFrame.lon_gps]
    name = "Trame LoRa"
    name_plural = "Trames LoRa"

class WifiDetectionAdmin(ModelView, model=WifiDetection):
    column_list = [WifiDetection.frame_id, WifiDetection.wifi_id, WifiDetection.rssi]
    name = "Détection"
    name_plural = "Détections"

admin_interface = Admin(app,engine)
admin_interface.add_view(WifiDeviceAdmin)
admin_interface.add_view(UplinkFrameAdmin)
admin_interface.add_view(WifiDetectionAdmin)
