from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

class WiFiAP(BaseModel):
    bssid: str
    rssi: int

class DecodedPayload(BaseModel):
    wifi_aps: List[WiFiAP]
    error: Optional[str] = None

class UplinkMessage(BaseModel):
    decoded_payload: DecodedPayload

class EndDeviceIDs(BaseModel):
    device_ids: str

class TTNWebhookPayload(BaseModel):
    end_device_ids : EndDeviceIDs
    uplink_message: UplinkMessage


app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

