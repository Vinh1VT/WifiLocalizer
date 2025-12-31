from fastapi import APIRouter,BackgroundTasks
from pydantic import BaseModel
from database import engine,UplinkFrame,WifiDetection,WifiDevice
from base64 import b64decode
from sqlmodel import Session,select


router = APIRouter()
# --- MODELES INPUT ---
class TTNUplinkMessage(BaseModel):
    frm_payload: str


class TTNWebhookData(BaseModel):
    uplink_message: TTNUplinkMessage


def process_uplink_data(payload_b64: str):

    print("Début du traitement en arrière-plan...")
    try:
        with Session(engine) as session:
            payload_bytes = b64decode(payload_b64)

            frame = UplinkFrame(lat_gps=None, lon_gps=None)
            session.add(frame)


            for i in range(0, len(payload_bytes), 7):
                if i + 7 <= len(payload_bytes):
                    bssid_bytes = payload_bytes[i:i + 6]
                    rssi = int.from_bytes([payload_bytes[i + 6]], 'big', signed=True)
                    bssid_str = ':'.join(f'{b:02X}' for b in bssid_bytes)

                    statement = select(WifiDevice).where(WifiDevice.bssid == bssid_str)
                    wifi_device = session.exec(statement).first()

                    if not wifi_device:
                        wifi_device = WifiDevice(bssid=bssid_str)
                        session.add(wifi_device)
                        session.flush()

                    detection = WifiDetection(
                        frame=frame,
                        wifi=wifi_device,
                        rssi=rssi
                    )
                    session.add(detection)

            session.commit()
            print(f"Succès background : Trame sauvegardée.")

    except Exception as e:
        print(f"Erreur critique dans le background task: {e}")

@router.post("/webhook")
async def ttn_webhook(data: TTNWebhookData, background_tasks: BackgroundTasks):
    payload = data.uplink_message.frm_payload
    background_tasks.add_task(process_uplink_data, payload)
    return {"status": "accepted"}