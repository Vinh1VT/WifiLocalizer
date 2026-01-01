# WifiLocalizer

School IoT
WifiLocalizer is a WiFi-based geolocation system. It consists of an ESP32 hardware sniffer and a Python backend for data processing and visualization.

## Project Structure

* **Carte/WifiSniffer/**: Firmware for ESP32. Scans WiFi networks and transmits BSSID/RSSI data via HTTP.
* **Serveur/**: Python FastAPI application.
    * `main.py`: Application entry point.
    * `database.py`: SQLite database models and configuration.
    * `routers/`: API endpoints for data ingestion, visualization, and calibration.

## How It Works

1.  **Data Collection**: The ESP32 device scans for nearby WiFi access points and posts the detected networks (MAC address and Signal Strength) to the server.
2.  **Ingestion**: The server records every access points and their signal strength as one frame.
3.  **Calibration**: A user assigns real GPS coordinates to a recorded frame via the web interface to establish ground truth.
4.  **Algorithm**:
    * **AP Localization**: The system calculates the estimated position of WiFi Access Points based on the calibrated frames.
    * **Tracking**: New incoming frames are automatically geolocated using the weighted average of the known Access Points' positions.
5.  **Visualization**: A web dashboard displays an interactive map showing real GPS points, estimated positions, and WiFi coverage zones.

## Usage

### Server
Start the FastAPI application located in the `Serveur` directory.

Access the web interface at the default local address:
* **Dashboard**: `/`
* **Map**: `/map`
* **Calibration**: `/admin-panel`
* **Database View**: `/db`

### Hardware (ESP32)
1.  Open `WifiSniffer.ino`.
2.  Update the `SSID`, `WIFI_PASSWD`, and `SERVER_URL` constants.
3.  Upload the code to an ESP32 board.

## Note
This branch uses a standard weighted centroid algorithm for positioning. An alternative implementation utilizing Machine Learning is available in the dedicated branch.
