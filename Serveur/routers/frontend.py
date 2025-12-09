from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session, WifiDevice, UplinkFrame
from fastapi.responses import HTMLResponse
import folium

router = APIRouter()


# --- PAGE D'ACCUEIL ---
@router.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
        <head>
            <title>Wifi Localizer</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: sans-serif; text-align: center; padding-top: 50px; background-color: #f8f9fa; }
                a { text-decoration: none; color: inherit; }
                .btn { display: inline-block; padding: 15px 30px; margin: 10px; border-radius: 8px; font-size: 18px; color: white; transition: 0.3s; }
                .btn-map { background-color: #28a745; }
                .btn-admin { background-color: #007bff; }
                .btn-db { background-color: #6c757d; }
                .btn:hover { opacity: 0.8; }
            </style>
        </head>
        <body>
            <h1>📡 Wifi Localizer</h1>
            <p>Projet de géolocalisation par triangulation WiFi</p>
            <br>
            <a href="/map" class="btn btn-map">🗺️ Voir la Carte Interactive</a><br>
            <a href="/admin-panel" class="btn btn-admin">🛠️ Valider des Trames (Admin)</a><br>
            <a href="/db" class="btn btn-db">🗄️ Voir la Base de Données</a>
        </body>
    </html>
    """


# --- CARTE INTERACTIVE ---
@router.get("/map", response_class=HTMLResponse)
def show_map(session: Session = Depends(get_session)):
    # 1. Récupération des données
    # On trie par date pour le tracé du chemin
    frames = session.exec(select(UplinkFrame).order_by(UplinkFrame.created_at)).all()
    # On ne prend que les WiFi qui ont une position estimée
    aps = session.exec(select(WifiDevice).where(WifiDevice.lat_estimated != None)).all()

    # 2. Centrage de la carte
    start_lat, start_lon = 48.8566, 2.3522  # Paris par défaut

    # On cherche la dernière position connue pour centrer la carte dessus
    valid_frames = [f for f in frames if f.lat_gps or f.lat_estimated]
    if valid_frames:
        last = valid_frames[-1]
        # Priorité au GPS, sinon l'estimé
        start_lat = last.lat_gps if last.lat_gps else last.lat_estimated
        start_lon = last.lon_gps if last.lon_gps else last.lon_estimated

    m = folium.Map(location=[start_lat, start_lon], zoom_start=16)

    # 3. Création des Groupes (Calques)
    fg_gps = folium.FeatureGroup(name="✅ Trames GPS (Réelles)")
    fg_est = folium.FeatureGroup(name="⚠️ Trames Estimées (Calcul)")
    fg_aps = folium.FeatureGroup(name="📡 Bornes WiFi (Estimées)")
    fg_path = folium.FeatureGroup(name="📈 Chemin Parcouru")

    path_points = []

    # 4. Ajout des Trames
    for frame in frames:
        time_str = frame.created_at.strftime('%H:%M:%S')

        # A. Cas GPS (Vert)
        if frame.lat_gps and frame.lon_gps:
            popup_txt = f"<b>Trame #{frame.id}</b><br>Source: GPS<br>Heure: {time_str}"
            folium.CircleMarker(
                location=[frame.lat_gps, frame.lon_gps],
                radius=6, color="green", fill=True, fill_color="green", fill_opacity=0.7,
                popup=popup_txt
            ).add_to(fg_gps)
            path_points.append((frame.lat_gps, frame.lon_gps))

        # B. Cas Estimé (Orange)
        elif frame.lat_estimated and frame.lon_estimated:
            popup_txt = f"<b>Trame #{frame.id}</b><br>Source: Triangulation<br>Heure: {time_str}"
            folium.CircleMarker(
                location=[frame.lat_estimated, frame.lon_estimated],
                radius=6, color="orange", fill=True, fill_color="orange", fill_opacity=0.7,
                popup=popup_txt
            ).add_to(fg_est)
            path_points.append((frame.lat_estimated, frame.lon_estimated))

    # 5. Tracé du chemin (Ligne Rouge)
    if len(path_points) > 1:
        folium.PolyLine(
            path_points, color="red", weight=3, opacity=0.6
        ).add_to(fg_path)

    # 6. Ajout des Bornes WiFi (Icônes Bleues)
    for ap in aps:
        if ap.lat_estimated and ap.lon_estimated:
            folium.Marker(
                location=[ap.lat_estimated, ap.lon_estimated],
                popup=f"<b>WiFi: {ap.bssid}</b><br>ID: {ap.id}",
                icon=folium.Icon(color="blue", icon="wifi", prefix="fa")
            ).add_to(fg_aps)

    # 7. Finalisation
    fg_path.add_to(m)
    fg_aps.add_to(m)
    fg_est.add_to(m)
    fg_gps.add_to(m)

    folium.LayerControl().add_to(m)

    return m.get_root().render()


# --- ADMIN PANEL (Validation GPS) ---
@router.get("/admin-panel", response_class=HTMLResponse)
def admin_dashboard(session: Session = Depends(get_session)):
    # Récupérer les trames SANS GPS, de la plus récente à la plus ancienne
    statement = select(UplinkFrame).where(UplinkFrame.lat_gps == None).order_by(UplinkFrame.created_at.desc())
    frames = session.exec(statement).all()

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin - Mapping</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; padding: 20px; background:#f0f0f0; }
            h1 { text-align: center; color: #333; }
            .frame-card { background:white; border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .info { color: #666; font-size: 0.9em; margin-bottom: 10px; }
            .btn { width:100%; padding: 12px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 5px; color: white; }
            .btn-gps { background-color: #007bff; }
            .btn-manual { background-color: #6c757d; }
            .nav { text-align: center; margin-bottom: 20px; }
            .nav a { margin: 0 10px; color: #007bff; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/">🏠 Accueil</a> | <a href="/map">🗺️ Carte</a>
        </div>
        <h1>Validation Terrain</h1>
    """

    if not frames:
        html_content += "<p style='text-align:center;'>✅ Aucune trame en attente. Tout est localisé !</p>"

    for frame in frames:
        count = len(frame.detections)
        html_content += f"""
        <div class="frame-card" id="card-{frame.id}">
            <h3>Trame #{frame.id}</h3>
            <div class="info">🕒 {frame.created_at.strftime('%H:%M:%S')} | 📡 {count} réseaux détectés</div>

            <button class="btn btn-gps" onclick="localizeFrame({frame.id})">📍 Je suis ICI (GPS)</button>
            <button class="btn btn-manual" onclick="manualLocalize({frame.id})">✏️ Saisir Manuellement</button>
        </div>
        """

    html_content += """
        <script>
            function localizeFrame(frameId) {
                const btn = document.querySelector(`#card-${frameId} .btn-gps`);
                btn.textContent = "⏳ Acquisition GPS...";
                btn.disabled = true;

                if (!navigator.geolocation) {
                    alert("Votre navigateur ne supporte pas le GPS.");
                    manualLocalize(frameId);
                    return;
                }

                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        sendPosition(frameId, pos.coords.latitude, pos.coords.longitude);
                    },
                    (err) => {
                        console.error(err);
                        alert("Erreur GPS ou Accès refusé (Essayez la saisie manuelle).");
                        btn.textContent = "📍 Je suis ICI (GPS)";
                        btn.disabled = false;
                    },
                    { enableHighAccuracy: true, timeout: 10000 }
                );
            }

            function manualLocalize(frameId) {
                let input = prompt("Entrez vos coordonnées 'LAT, LON' (ex: 48.8566, 2.3522) :");
                if (input) {
                    // Remplacement des virgules par des points si l'utilisateur se trompe
                    input = input.replace(',', '.'); 
                    // Si l'utilisateur a mis un espace ou un point-virgule comme séparateur
                    let parts;
                    if (input.includes(' ')) parts = input.split(' ');
                    else if (input.includes(';')) parts = input.split(';');
                    else parts = input.split(','); // Séparateur standard si formaté proprement

                    // Nettoyage un peu bourrin pour trouver 2 nombres
                    let coords = input.match(/-?\d+(\.\d+)?/g);

                    if(coords && coords.length >= 2) {
                        sendPosition(frameId, parseFloat(coords[0]), parseFloat(coords[1]));
                    } else {
                        alert("Format invalide. Essayez '48.123, 2.456'");
                    }
                }
            }

            async function sendPosition(frameId, lat, lon) {
                try {
                    let res = await fetch(`/admin/frame/${frameId}/localize`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ lat: lat, lon: lon })
                    });

                    if (res.ok) {
                        // Animation de suppression
                        let card = document.getElementById(`card-${frameId}`);
                        card.style.opacity = '0';
                        setTimeout(() => card.remove(), 300);
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