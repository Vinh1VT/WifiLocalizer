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
    frames = session.exec(select(UplinkFrame).order_by(UplinkFrame.created_at)).all()
    aps = session.exec(select(WifiDevice).where(WifiDevice.lat_estimated != None)).all()

    # 2. Centrage (sur la dernière position connue)
    start_lat, start_lon = 48.85, 2.35
    valid_frames = [f for f in frames if f.lat_gps or f.lat_estimated or f.lat_ml]
    if valid_frames:
        last = valid_frames[-1]
        # Priorité : GPS > IA > Barycentre
        start_lat = last.lat_gps or last.lat_ml or last.lat_estimated
        start_lon = last.lon_gps or last.lon_ml or last.lon_estimated

    m = folium.Map(location=[start_lat, start_lon], zoom_start=18)

    # 3. Création des Groupes (Calques)
    fg_gps = folium.FeatureGroup(name="✅ Vérité Terrain (GPS)")
    fg_algo = folium.FeatureGroup(name="⚠️ Algo Barycentre (Classique)")
    fg_ml = folium.FeatureGroup(name="🧠 IA / Machine Learning (Violet)")
    fg_links = folium.FeatureGroup(name="📏 Lignes d'erreur (Comparaison)")
    fg_aps = folium.FeatureGroup(name="📡 Bornes WiFi")

    for frame in frames:
        popup_base = f"<b>Trame #{frame.id}</b><br>{frame.created_at.strftime('%H:%M:%S')}"

        # A. VÉRITÉ TERRAIN (Vert)
        if frame.lat_gps:
            folium.CircleMarker(
                location=[frame.lat_gps, frame.lon_gps],
                radius=5, color="green", fill=True, fill_opacity=1,
                popup=f"{popup_base}<br>📍 Position Réelle"
            ).add_to(fg_gps)

        # B. ALGO CLASSIQUE (Orange)
        if frame.lat_estimated:
            folium.CircleMarker(
                location=[frame.lat_estimated, frame.lon_estimated],
                radius=4, color="orange", fill=True, fill_opacity=0.6,
                popup=f"{popup_base}<br>📐 Algo Barycentre"
            ).add_to(fg_algo)

            # Ligne Erreur Algo (si on a le GPS)
            if frame.lat_gps:
                folium.PolyLine(
                    [[frame.lat_gps, frame.lon_gps], [frame.lat_estimated, frame.lon_estimated]],
                    color="orange", weight=1, opacity=0.5, dash_array='5, 5'
                ).add_to(fg_links)

        # C. MACHINE LEARNING (Violet)
        if frame.lat_ml:
            folium.CircleMarker(
                location=[frame.lat_ml, frame.lon_ml],
                radius=4, color="purple", fill=True, fill_opacity=0.8,
                popup=f"{popup_base}<br>🧠 Prédiction IA"
            ).add_to(fg_ml)

            # Ligne Erreur IA (si on a le GPS)
            if frame.lat_gps:
                folium.PolyLine(
                    [[frame.lat_gps, frame.lon_gps], [frame.lat_ml, frame.lon_ml]],
                    color="purple", weight=2, opacity=0.8
                ).add_to(fg_links)

    # 4. Affichage Bornes
    for ap in aps:
        folium.CircleMarker(
            location=[ap.lat_estimated, ap.lon_estimated],
            radius=2, color="blue", popup=f"AP: {ap.bssid}"
        ).add_to(fg_aps)

    # Ajout des calques
    fg_links.add_to(m)  # En premier pour être dessous
    fg_aps.add_to(m)
    fg_algo.add_to(m)
    fg_ml.add_to(m)
    fg_gps.add_to(m)

    folium.LayerControl().add_to(m)

    return m.get_root().render()


# --- ADMIN PANEL (Validation GPS) ---
@router.get("/admin-panel", response_class=HTMLResponse)
def admin_dashboard(session: Session = Depends(get_session)):
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