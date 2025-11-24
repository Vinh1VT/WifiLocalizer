# routers/frontend.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session, WifiDevice
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def read_dashboard(session: Session = Depends(get_session)):
    # 1. On récupère les données
    wifis = session.exec(select(WifiDevice)).all()

    # 2. On construit une petite liste HTML (très basique)
    html_content = """
    <html>
        <head><title>Mon Dashboard WiFi</title></head>
        <body>
            <h1>Wifis Détectés</h1>
            <ul>
    """

    for wifi in wifis:
        html_content += f"<li>{wifi.bssid} (ID: {wifi.id})</li>"

    html_content += """
            </ul>
        </body>
    </html>
    """
    return html_content