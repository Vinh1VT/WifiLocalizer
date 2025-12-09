/*
 * ESP32 WiFi Scanner & HTTP Sender
 * Pour le projet WifiLocalizer
 * * Envoie les réseaux détectés via HTTP POST au format JSON.
 */

#include <WiFi.h>
#include <HTTPClient.h>

// --- CONFIGURATION ---
const char* ssid = "Vinh";        // Le WiFi pour se connecter à Internet/Serveur
const char* password = "PlanteVerte";

// ⚠️ REMPLACE 192.168.X.X par l'IP locale de ton PC qui fait tourner le serveur FastAPI
// Garde le port 8000 et le chemin /ingest/
const char* serverUrl = "http://vps-98cd652a.vps.ovh.net:8012/algo"; 

// --- FILTRE MAC ---
bool MACFilter(uint8_t* MAC){
  // Filtre les adresses locales/randomisées (bit 1 du premier octet à 1)
  if(MAC[0] & 0x02){
    return false;
  }
  return true;
}

// --- UTILITAIRE FORMATAGE MAC ---
String macToString(uint8_t* mac) {
  String s = "";
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 16) s += "0";
    s += String(mac[i], HEX);
    if (i < 5) s += ":"; // Ajoute les deux-points pour le format standard
  }
  s.toUpperCase();
  return s;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Connexion WiFi
  Serial.println();
  Serial.print("Connexion a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connecte.");
  Serial.print("Adresse IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 1. SCAN DES RÉSEAUX
  Serial.println("Scan des reseaux...");
  int numSsid = WiFi.scanNetworks();
  
  if (numSsid == -1) {
    Serial.println("Erreur de scan WiFi");
  } else {
    Serial.print(numSsid);
    Serial.println(" reseaux trouves.");

    // 2. CONSTRUCTION DU JSON
    // On veut obtenir : {"networks": [{"bssid": "XX:XX...", "rssi": -80}, ...]}
    
    String jsonPayload = "{\"networks\": [";
    int count = 0;

    for (int i = 0; i < numSsid; i++) {
      uint8_t* bssidIn = WiFi.BSSID(i);
      
      // Application du filtre
      if (MACFilter(bssidIn)) {
        // Si ce n'est pas le premier élément, on ajoute une virgule
        if (count > 0) {
          jsonPayload += ",";
        }
        
        jsonPayload += "{\"bssid\": \"";
        jsonPayload += macToString(bssidIn);
        jsonPayload += "\", \"rssi\": ";
        jsonPayload += WiFi.RSSI(i);
        jsonPayload += "}";
        
        count++;
      }
    }
    jsonPayload += "]}";

    // 3. ENVOI HTTP (Si on a trouvé des réseaux valides)
    if (count > 0) {
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        
        Serial.println("Envoi au serveur...");
        // Serial.println(jsonPayload); // Decommenter pour debugguer le JSON

        http.begin(serverUrl);
        http.addHeader("Content-Type", "application/json");

        int httpResponseCode = http.POST(jsonPayload);

        if (httpResponseCode > 0) {
          String response = http.getString();
          Serial.print("Code HTTP: ");
          Serial.println(httpResponseCode);
          Serial.print("Reponse: ");
          Serial.println(response);
        } else {
          Serial.print("Erreur lors de l'envoi: ");
          Serial.println(httpResponseCode);
        }
        
        http.end();
      } else {
        Serial.println("Erreur: WiFi deconnecté");
      }
    } else {
      Serial.println("Aucun reseau valide apres filtrage.");
    }
  }

  // Nettoyage de la mémoire du scan
  WiFi.scanDelete();

  // Attendre avant le prochain scan (ex: 10 secondes)
  Serial.println("Attente 10s...");
  delay(10000);
}