from fastapi import APIRouter, Depends,HTTPException
from pydantic import BaseModel
from sqlmodel import Session,select
from database import get_session,UplinkFrame

router = APIRouter()

class GPSUpdate(BaseModel):
    lat: float
    lon: float

@router.patch("/frame/{frame_id}/localize")
async def update_frame_location(frame_id:int,gps_data:GPSUpdate,session:Session = Depends(get_session)):
    frame = session.get(UplinkFrame,frame_id)

    if not frame :
        raise HTTPException(status_code=404,detail="Frame not found")

    frame.lat_gps = gps_data.lat
    frame.lon_gps = gps_data.lon

    session.add(frame)
    session.commit()
    session.refresh(frame)

    return {"status": "updated", "frame_id": frame.id, "new_pos": {frame.lat_gps, frame.lon_gps}}