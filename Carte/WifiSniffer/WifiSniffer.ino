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
  //listNetworks();
  sendLoraPayload();
  delay(60000);
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

String bytesToHex(const byte* bytes, int len){
  String hex = "";
  for (int i = 0; i<len;i++){
    if (bytes[i] < 16){
      hex += "0";
    }
    hex += String(bytes[i],HEX);
  }
  return hex;
}

//nombre max de point d'acces / payload
#define MAX_PAYLOAD 7

void sendLoraPayload(){
    // scan for nearby networks:
  Serial.println("** Scan Networks **");
  int numSsid = WiFi.scanNetworks();
  if (numSsid == -1) {
    Serial.println("Couldn't get a wifi connection");
    while (true);
  }

  // print the list of networks seen:
  Serial.print("number of available networks:");
  Serial.println(numSsid);
  
  byte payload[MAX_PAYLOAD * 7];
  int payloadIndex = 0;
  int numApsToSend = min(numSsid,MAX_PAYLOAD);

  // print the network number and name for each network found:
  int thisNet = 0;
  int filteredNets = 0;
  while(thisNet < numSsid && filteredNets < MAX_PAYLOAD){
    //To serial, only for debug
    /*Serial.print("\n");
    Serial.print(thisNet);
    Serial.print(") ");
    Serial.print(WiFi.SSID(thisNet));
    Serial.print("\tSignal: ");
    Serial.print(WiFi.RSSI(thisNet));
    Serial.print(" dBm");*/

    //Filter the BSSID
    byte MacAdress[6]; 
    memcpy(MacAdress,WiFi.BSSID(thisNet),6);
    if (MACFilter(MacAdress)){
      //Add to payload
      memcpy(&payload[payloadIndex],MacAdress,6);
      payloadIndex += 6;
      payload[payloadIndex] = (int8_t)WiFi.RSSI(thisNet);
      payloadIndex+=1;
      filteredNets++;
    }
    
    thisNet++;
  }

  String hexPayload = bytesToHex(payload,payloadIndex);
  hexPayload.toUpperCase();
  String command = "AT+MSGHEX=" + hexPayload;

  //Serial only for debug
  Serial.println("\n\n --- LORA PAYLOAD ---");
  Serial.print("Payload : ");
  Serial.println(hexPayload);
  Serial.print("Payload size : ");
  Serial.println(payloadIndex);

  //Sends the byte
  Serial2.println(command);
}

bool MACFilter(byte* MAC){

  if(MAC[0] & 0x02){
    return false;
  }
  return true;
}

void listNetworks() {
  // scan for nearby networks:
  //For debug purposes
  Serial.println("** Scan Networks **");
  int numSsid = WiFi.scanNetworks();
  if (numSsid == -1) {
    Serial.println("Couldn't get a wifi connection");
    while (true);
  }

  // print the list of networks seen:
  Serial.print("number of available networks:");
  Serial.println(numSsid);

  // print the network number and name for each network found:
  for (int thisNet = 0; thisNet < numSsid; thisNet++) {
    byte MacAdress[6]; 
    memcpy(MacAdress,WiFi.BSSID(thisNet),6);
    Serial.print("\n");
    Serial.print(thisNet);
    Serial.print(") ");
    Serial.print(WiFi.SSID(thisNet));
    Serial.print("\tSignal: ");
    Serial.print(WiFi.RSSI(thisNet));
    Serial.print(" dBm");
    Serial.print("Temp : ");
    Serial.print(MACFilter(MacAdress));

    

  }
}

void receiveMessageSerial2(){
  while(Serial2.available()){
    Serial.write(Serial2.read());
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