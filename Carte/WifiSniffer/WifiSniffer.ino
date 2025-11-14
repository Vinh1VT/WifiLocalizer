/*

 This example  prints the Wifi shield's MAC address, and
 scans for available Wifi networks using the Wifi shield.
 Every ten seconds, it scans again. It doesn't actually
 connect to any network, so no encryption scheme is specified.

 Circuit:
 * WiFi shield attached

 created 13 July 2010
 by dlf (Metodo2 srl)
 modified 21 Junn 2012
 by Tom Igoe and Jaymes Dec
 */

 /*
 Modified for a Wifi Localizer application
 by Vinh VO TUAN
  11/2025
 
 */


#include <SPI.h>
#include <WiFi.h>



#define RX2_PIN 16
#define TX2_PIN 17



void setup() {
  //Initialize serial and wait for port to open:
  Serial.begin(115200);
  Serial2.begin(9600,SERIAL_8N1,RX2_PIN,TX2_PIN);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB port only
  }
  // Print WiFi MAC address:
  printMacAddress();
  setupLora();
}

void loop() {
  // scan for existing networks:
  Serial.println("Scanning available networks...");
  listNetworks();
  delay(10000);
}

void printMacAddress() {
  // the MAC address of your Wifi shield
  byte mac[6];

  // print your MAC address:
  WiFi.macAddress(mac);
  Serial.print("MAC: ");
  Serial.print(mac[5], HEX);
  Serial.print(":");
  Serial.print(mac[4], HEX);
  Serial.print(":");
  Serial.print(mac[3], HEX);
  Serial.print(":");
  Serial.print(mac[2], HEX);
  Serial.print(":");
  Serial.print(mac[1], HEX);
  Serial.print(":");
  Serial.println(mac[0], HEX);
}

void listNetworks() {
  // scan for nearby networks:
  Serial.println("** Scan Networks **");
  int numSsid = WiFi.scanNetworks();w
  if (numSsid == -1) {
    Serial.println("Couldn't get a wifi connection");
    while (true);
  }

  // print the list of networks seen:
  Serial.print("number of available networks:");
  Serial.println(numSsid);

  // print the network number and name for each network found:
  for (int thisNet = 0; thisNet < numSsid; thisNet++) {
    Serial.print("\n");
    Serial.print(thisNet);
    Serial.print(") ");
    Serial.print(WiFi.SSID(thisNet));
    Serial.print("\tSignal: ");
    Serial.print(WiFi.RSSI(thisNet));
    Serial.print(" dBm");
  }
}

void receiveMessageSerial2(){
  if (Serial2.available()) {
    String msg = Serial2.readStringUntil('\n');
    Serial.print("Reçu du périphérique: ");
    Serial.println(msg);
  }
}

void waitForJoin() {
  while (true) {
    if (Serial2.available()) {
      String msg = Serial2.readStringUntil('\n');
      msg.trim();
      Serial.println(msg);
      if (msg.indexOf("+JOIN: Done") != -1) break;
    }
  }
}


void setupLora(){

  Serial2.println("AT+DR=EU868");
  receiveMessageSerial2();
  delay(1000);

  Serial2.println("AT+ID=DevEUI,70B3D57ED0074060");
  receiveMessageSerial2();
  delay(1000);

  Serial2.println("AT+ID=AppEUI,0000000000000000");
  receiveMessageSerial2();
  delay(1000);

  Serial2.println("AT+KEY=APPKEY,AB69B9D29A86812C74D19A298F457DD5");
  receiveMessageSerial2();
  delay(1000);

  Serial2.println("AT+MODE=LWOTAA");
  receiveMessageSerial2();
  delay(1000);

  Serial2.println("AT+DR=DR3");
  receiveMessageSerial2();
  delay(2000);

  Serial2.println("AT+JOIN");
  waitForJoin();

  Serial.println("Config finie");
}