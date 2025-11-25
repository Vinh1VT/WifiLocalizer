# routers/frontend.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session, WifiDevice,UplinkFrame
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


@router.get("/localizeframe", response_class=HTMLResponse)
def admin_dashboard(session: Session = Depends(get_session)):
    # On ne récupère que les trames qui n'ont PAS encore de GPS
    statement = select(UplinkFrame).where(UplinkFrame.lat_gps == None).order_by(UplinkFrame.created_at.desc())
    frames = session.exec(statement).all()

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin - Mapping</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; padding: 20px; }
            .frame-card { border: 1px solid #ccc; padding: 15px; margin-bottom: 10px; border-radius: 8px; }
            .btn { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn:disabled { background-color: #ccc; }
        </style>
    </head>
    <body>
        <h1>Admin Mapping</h1>
        <p>Trames en attente de localisation :</p>

        <div id="frames-list">
    """

    for frame in frames:
        count = len(frame.detections)
        html_content += f"""
        <div class="frame-card" id="card-{frame.id}">
            <h3>Trame #{frame.id}</h3>
            <p>Reçue le : {frame.created_at.strftime('%H:%M:%S')}</p>
            <p>Wi-Fi détectés : <strong>{count}</strong></p>
            <button class="btn" onclick="localizeFrame({frame.id})">📍 ICI (Ma position)</button>
        </div>
        """

    html_content += """
        </div>

        <script>
            function localizeFrame(frameId) {
                if (!navigator.geolocation) {
                    alert("La géolocalisation n'est pas supportée par votre navigateur.");
                    return;
                }

                const btn = document.querySelector(`#card-${frameId} button`);
                btn.textContent = "⏳ Acquisition GPS...";
                btn.disabled = true;

                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;

                        // Envoi au backend
                        sendPositionToBackend(frameId, lat, lon);
                    },
                    (error) => {
                        alert("Erreur GPS : " + error.message);
                        btn.textContent = "📍 ICI (Réessayer)";
                        btn.disabled = false;
                    },
                    { enableHighAccuracy: true } // Important pour la précision
                );
            }

            async function sendPositionToBackend(frameId, lat, lon) {
                try {
                    const response = await fetch(`/admin/frame/${frameId}/localize`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ lat: lat, lon: lon })
                    });

                    if (response.ok) {
                        // On supprime la carte visuellement car elle est traitée
                        document.getElementById(`card-${frameId}`).remove();
                        alert(`Trame ${frameId} localisée avec succès !`);
                    } else {
                        alert("Erreur serveur lors de la sauvegarde.");
                    }
                } catch (e) {
                    console.error(e);
                    alert("Erreur réseau.");
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content