from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List
from sqlmodel import Session, select
from database import engine, UplinkFrame, WifiDevice, WifiDetection

router = APIRouter()


# --- Modèles pour le JSON entrant ---
class WifiItem(BaseModel):
    bssid: str
    rssi: int


class FramePayload(BaseModel):
    networks: List[WifiItem]


# --- Fonctions Utilitaires ---
def rssi_to_weight(rssi: int) -> float:
    # Plus le signal est fort (proche de 0), plus le poids est grand
    # E.g. -50dBm > -90dBm
    return pow(10, rssi / 10.0)


def try_localize_frame(session: Session, frame: UplinkFrame):
    """Essaie d'estimer la position de la trame via les AP connus."""
    sum_lat = 0.0
    sum_lon = 0.0
    sum_weights = 0.0
    count = 0

    frame_refreshed = session.get(UplinkFrame, frame.id)

    for detection in frame_refreshed.detections:
        wifi = detection.wifi
        # Si cet AP a une position connue (estimée)
        if wifi.lat_estimated is not None and wifi.lon_estimated is not None:
            w = rssi_to_weight(detection.rssi)
            sum_lat += wifi.lat_estimated * w
            sum_lon += wifi.lon_estimated * w
            sum_weights += w
            count += 1

    if count > 0 and sum_weights > 0:
        frame.lat_estimated = sum_lat / sum_weights
        frame.lon_estimated = sum_lon / sum_weights
        session.add(frame)
        session.commit()
        print(f"Trame {frame.id} estimée à : {frame.lat_estimated}, {frame.lon_estimated}")


def process_frame(payload: FramePayload):
    """Sauvegarde les données et lance l'estimation."""
    with Session(engine) as session:
        # 1. Créer la trame (sans GPS pour l'instant)
        frame = UplinkFrame()
        session.add(frame)
        session.flush()

        # 2. Enregistrer les detections
        for net in payload.networks:
            # Récupérer ou Créer le WifiDevice
            wifi = session.exec(select(WifiDevice).where(WifiDevice.bssid == net.bssid)).first()
            if not wifi:
                wifi = WifiDevice(bssid=net.bssid)
                session.add(wifi)
                session.flush()

            # Lier la détection
            det = WifiDetection(frame_id=frame.id, wifi_id=wifi.id, rssi=net.rssi)
            session.add(det)

        session.commit()

        # 3. Tenter la triangulation immédiate (tracking)
        try_localize_frame(session, frame)


@router.post("/")
async def ingest_http(payload: FramePayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_frame, payload)
    return {"status": "ok", "message": "Frame received"}