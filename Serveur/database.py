from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, create_engine, Session
from typing import List, Optional

# --- CONFIG DATABASE ---
sqlite_file = "wifi_ap.db"
sqlite_url = f"sqlite:///{sqlite_file}"

engine = create_engine(sqlite_url, echo=False, connect_args={"check_same_thread": False})


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


class WifiDetection(SQLModel, table=True):
    wifi_id: Optional[int] = Field(default=None, foreign_key="wifidevice.id", primary_key=True)
    frame_id: Optional[int] = Field(default=None, foreign_key="uplinkframe.id", primary_key=True)
    rssi: int
    wifi: "WifiDevice" = Relationship(back_populates="detections")
    frame: "UplinkFrame" = Relationship(back_populates="detections")


class WifiDevice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bssid: str = Field(index=True, unique=True)

    # Position ESTIMÉE
    lat_estimated: Optional[float] = Field(default=None)
    lon_estimated: Optional[float] = Field(default=None)

    # --- AJOUT MANQUANT ---
    last_calculated_at: Optional[datetime] = Field(default=None)

    detections: List["WifiDetection"] = Relationship(back_populates="wifi")


class UplinkFrame(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Position RÉELLE (Vérité Terrain)
    lat_gps: Optional[float] = Field(default=None)
    lon_gps: Optional[float] = Field(default=None)

    # Position ESTIMÉE (Barycentre Classique)
    lat_estimated: Optional[float] = Field(default=None)
    lon_estimated: Optional[float] = Field(default=None)

    # --- AJOUT : Position ESTIMÉE par IA (Machine Learning) ---
    lat_ml: Optional[float] = Field(default=None)
    lon_ml: Optional[float] = Field(default=None)

    detections: List["WifiDetection"] = Relationship(back_populates="frame")