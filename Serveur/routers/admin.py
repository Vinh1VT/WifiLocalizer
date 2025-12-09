from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session, UplinkFrame, WifiDevice, WifiDetection

router = APIRouter()


class GPSUpdate(BaseModel):
    lat: float
    lon: float


def rssi_to_weight(rssi: int) -> float:
    return pow(10, rssi / 10.0)


def recalculate_ap_positions(session: Session, frame_id: int):
    """
    Appelé quand une trame reçoit un GPS valide.
    Met à jour la position estimée des APs présents dans cette trame.
    """
    frame = session.get(UplinkFrame, frame_id)
    if not frame:
        return

    print(f"Recalcul des APs pour la trame {frame_id}...")

    for detection in frame.detections:
        wifi = detection.wifi

        # Pour ce Wifi, on récupère TOUTES les trames qui l'ont vu ET qui ont un GPS
        query = select(WifiDetection).join(UplinkFrame).where(
            WifiDetection.wifi_id == wifi.id,
            UplinkFrame.lat_gps != None  # On utilise uniquement les données "sûres"
        )
        all_detections = session.exec(query).all()

        if not all_detections:
            continue

        w_lat = 0.0
        w_lon = 0.0
        total_weight = 0.0

        for det in all_detections:
            # On pondère la position GPS de la trame par la force du signal
            w = rssi_to_weight(det.rssi)
            w_lat += det.frame.lat_gps * w
            w_lon += det.frame.lon_gps * w
            total_weight += w

        if total_weight > 0:
            wifi.lat_estimated = w_lat / total_weight
            wifi.lon_estimated = w_lon / total_weight
            session.add(wifi)
            print(f" -> AP {wifi.bssid} mis à jour : {wifi.lat_estimated}, {wifi.lon_estimated}")

    session.commit()


@router.patch("/frame/{frame_id}/localize")
async def update_frame_location(
        frame_id: int,
        gps_data: GPSUpdate,
        background_tasks: BackgroundTasks,
        session: Session = Depends(get_session)
):
    frame = session.get(UplinkFrame, frame_id)
    if not frame:
        raise HTTPException(status_code=404, detail="Frame not found")

    # 1. Mise à jour du GPS de la trame
    frame.lat_gps = gps_data.lat
    frame.lon_gps = gps_data.lon
    session.add(frame)
    session.commit()
    session.refresh(frame)

    # 2. Lancer le recalcul des positions WiFi en arrière-plan
    # (On passe l'ID et on rouvrira une session dans la tache de fond si besoin,
    # mais ici on peut le faire en synchrone si c'est rapide, ou via background task)
    # Pour simplifier ici, on le fait directement :
    recalculate_ap_positions(session, frame_id)

    return {"status": "updated", "frame_id": frame.id}