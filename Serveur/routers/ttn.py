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


# --- LOGIQUE MÉTIER (Déplacée hors de la vue) ---
def process_uplink_data(payload_b64: str):
    """
    Cette fonction s'exécute en arrière-plan.
    Elle ouvre sa PROPRE session (très important).
    """
    print("Début du traitement en arrière-plan...")
    try:
        # On ouvre une session manuellement car on est hors du cycle Requête/Réponse
        with Session(engine) as session:
            payload_bytes = b64decode(payload_b64)

            # 1. Création de la Trame
            frame = UplinkFrame(lat_gps=None, lon_gps=None)
            session.add(frame)
            # On ne commit pas encore, on laisse la transaction ouverte

            detections_to_add = []

            # 2. Boucle de lecture
            for i in range(0, len(payload_bytes), 7):
                if i + 7 <= len(payload_bytes):
                    bssid_bytes = payload_bytes[i:i + 6]
                    rssi = int.from_bytes([payload_bytes[i + 6]], 'big', signed=True)
                    bssid_str = ':'.join(f'{b:02X}' for b in bssid_bytes)

                    # Vérif ou Création du WifiDevice
                    statement = select(WifiDevice).where(WifiDevice.bssid == bssid_str)
                    wifi_device = session.exec(statement).first()

                    if not wifi_device:
                        wifi_device = WifiDevice(bssid=bssid_str)
                        session.add(wifi_device)
                        # Astuce: flush() envoie l'ID à la DB sans commiter la transaction entière
                        session.flush()

                        # Création de la détection liée
                    detection = WifiDetection(
                        frame=frame,  # On lie l'objet frame directement
                        wifi=wifi_device,  # On lie l'objet wifi directement
                        rssi=rssi
                    )
                    session.add(detection)

            # 3. UN SEUL COMMIT À LA FIN (Beaucoup plus rapide)
            session.commit()
            print(f"Succès background : Trame sauvegardée.")

    except Exception as e:
        print(f"Erreur critique dans le background task: {e}")
        # Ici tu pourrais logger l'erreur dans un fichier ou Sentry

@router.post("/webhook") # Note que le chemin est relatif
async def ttn_webhook(data: TTNWebhookData, background_tasks: BackgroundTasks):
    payload = data.uplink_message.frm_payload
    background_tasks.add_task(process_uplink_data, payload)
    return {"status": "accepted"}