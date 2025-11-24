from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
import base64

app = FastAPI()

class WiFiAP(BaseModel):
    bssid: str
    rssi: int

class TTNUplinkMessage(BaseModel):
    frm_payload: str  # This will be base64 encoded

class TTNWebhookData(BaseModel):
    uplink_message: TTNUplinkMessage

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/ttn")
async def ttn_webhook(data: TTNWebhookData):
    """
    Endpoint to receive data from The Things Network (TTN).
    The payload is expected to be in data.uplink_message.frm_payload,
    base64 encoded.
    """
    try:
        payload_b64 = data.uplink_message.frm_payload
        payload_bytes = base64.b64decode(payload_b64)

        wifi_aps = []
        # Each AP data is 7 bytes long (6 for BSSID, 1 for RSSI)
        for i in range(0, len(payload_bytes), 7):
            if i + 7 <= len(payload_bytes):
                bssid_bytes = payload_bytes[i:i+6]
                rssi = int.from_bytes([payload_bytes[i+6]], 'big', signed=True)
                
                bssid_str = ':'.join(f'{b:02X}' for b in bssid_bytes)
                
                wifi_aps.append(WiFiAP(bssid=bssid_str, rssi=rssi))
        
        print("Received and parsed WiFi APs:", wifi_aps)
        return {"status": "success", "parsed_data": wifi_aps}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

