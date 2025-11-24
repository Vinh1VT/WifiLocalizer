from fastapi import FastAPI, BackgroundTasks  # Pas besoin de Depends pour la session ici
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from base64 import b64decode
from sqlmodel import Field, SQLModel, create_engine, Relationship, Session, select

# --- CONFIG DATABASE ---
sqlite_file = "wifi_ap.db"
sqlite_url = f"sqlite:///{sqlite_file}"

# check_same_thread=False est crucial pour SQLite avec FastAPI
engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


app = FastAPI()


# --- MODELES DB (Inchangés) ---
class WifiDetection(SQLModel, table=True):
    wifi_id: Optional[int] = Field(default=None, foreign_key="wifidevice.id", primary_key=True)
    frame_id: Optional[int] = Field(default=None, foreign_key="uplinkframe.id", primary_key=True)
    rssi: int
    wifi: "WifiDevice" = Relationship(back_populates="detections")
    frame: "UplinkFrame" = Relationship(back_populates="detections")


class WifiDevice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bssid: str = Field(index=True, unique=True)
    lat_estimated: Optional[float] = Field(default=None)
    lon_estimated: Optional[float] = Field(default=None)
    last_calculated_at: Optional[datetime] = None
    detections: List["WifiDetection"] = Relationship(back_populates="wifi")


class UplinkFrame(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    lat_gps: Optional[float] = Field(default=None)
    lon_gps: Optional[float] = Field(default=None)
    detections: List["WifiDetection"] = Relationship(back_populates="frame")


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


# --- APP ---
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/ttn")
async def ttn_webhook(
        data: TTNWebhookData,
        background_tasks: BackgroundTasks
):
    """
    Répond instantanément à TTN et lance le travail après.
    """
    # On extrait juste la string nécessaire
    payload = data.uplink_message.frm_payload

    # On délègue le travail lourd
    background_tasks.add_task(process_uplink_data, payload)

    # On répond tout de suite (temps de réponse < 10ms)
    return {"status": "accepted", "message": "Processing in background"}