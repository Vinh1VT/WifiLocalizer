/*
 * ESP32 WiFi Scanner & HTTP Sender
 * Pour le projet WifiLocalizer
 * * Envoie les réseaux détectés via HTTP POST au format JSON.
 */

#include <WiFi.h>
#include <HTTPClient.h>

//Parameters
#define SSID "Vinh"
#define WIFI_PASSWD "PlanteVerte"
#define SERVER_URL  "http://vps-98cd652a.vps.ovh.net:8012/algo/"


#define DEBUG 0 //Set to 1 for serial messages

// --- CONFIGURATION ---
const char* ssid = SSID;
const char* password = WIFI_PASSWD;

const char* serverUrl = SERVER_URL;

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
    if (i < 5) s += ":";
  }
  s.toUpperCase();
  return s;
}

void setup() {
  if (DEBUG) Serial.begin(115200);
  delay(1000);

  // Connexion WiFi
  if (DEBUG){
    Serial.println();
    Serial.print("Connexion a ");
    Serial.println(ssid);
  }

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);

    if (DEBUG) Serial.print(".");
  }

  if (DEBUG){
    Serial.println("");
    Serial.println("WiFi connecte.");
    Serial.print("Adresse IP: ");
    Serial.println(WiFi.localIP());
  }
}

void loop() {
  // 1. SCAN DES RÉSEAUX
  if (DEBUG) Serial.println("Scan des reseaux...");
  int numSsid = WiFi.scanNetworks();
  
  if (numSsid == -1) {
    if (DEBUG) Serial.println("Erreur de scan WiFi");
  } else {
    if (DEBUG) {
      Serial.print(numSsid);
      Serial.println(" reseaux trouves.");
    }

    // 2. CONSTRUCTION DU JSON
    // Sous la forme : {"networks": [{"bssid": "XX:XX...", "rssi": -80}, ...]}
    
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
        
        if(DEBUG){
            Serial.println("Envoi au serveur...");
            Serial.println(jsonPayload);
        }

        http.begin(serverUrl);
        http.addHeader("Content-Type", "application/json");

        int httpResponseCode = http.POST(jsonPayload);

        if (DEBUG) {
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
        }
        
        http.end();
      } else {
        if (DEBUG) Serial.println("Erreur: WiFi deconnecté");
      }
    } else {
      if (DEBUG) Serial.println("Aucun reseau valide apres filtrage.");
    }
  }

  WiFi.scanDelete();

  if (DEBUG) Serial.println("Attente 10s...");
  delay(10000);
}