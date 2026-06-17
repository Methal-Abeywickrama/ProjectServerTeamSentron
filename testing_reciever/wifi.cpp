#include <WiFi.h>

// 1. Network Credentials
const char* ssid = "Mushab";
const char* password = "mushab123";

// 2. Raspberry Pi Server Details
const char* serverAddress = "192.168.43.49"; // Replace with your Raspi's IP
const uint16_t serverPort = 5555;            // Replace with your server's port
const long timeOutPeriod = 3000;
const String lockerAddress = "001";
const int lockerAddress = 8;

// Initialize the Wi-Fi client
WiFiClient client;

String getUserInput() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    return input;
  }
  return ""; 
}

void sendRequest(String message){
  if (message != ""){
    client.println(message); 
    Serial.print("Sent payload: ");
    Serial.println(message);
  }
  else{
    Serial.println("Empty input");
  }
}

String getResponse(long timeOutPeriodMS){
  long startTime = millis();

  while (client.available() == 0) {
    if (millis() - startTime > timeOutPeriod) {
      Serial.println(">>> Error: Server Timeout! No response received.");
      return ""; // Return an empty string if it times out
    }
  }
  
  String finalReply = "";
  while (client.available()) {
    finalReply = client.readStringUntil('\n');
  }
  // CRITICAL: Clean off any hidden \r or spaces before returning
  finalReply.trim(); 
  
  return finalReply;
}

void validation(String ID){
  String message = "GET " + lockerAddress + " MTCH " + ID;
  sendRequest(message);
  String reply = getResponse(timeOutPeriod);
  if (reply.substring(0,2)  == "OK"){
    Serial.println("Successfull");
  }
  else{
    Serial.println("Bad Commands");
  }
}

void lock(String ID){
  String message = "PUT " + lockerAddress + " BLNK " + ID;
  sendRequest(message);
  String reply = getResponse(timeOutPeriod);
  if ((reply.substring(0,2)  == "OK") && (reply.charAt(0))){
    Serial.println("Successfull");
  }
  else{
    Serial.println("Bad Commands");
  }
}


void setup() {
  Serial.begin(115200);
  delay(10);

  // Connect to Wi-Fi
  Serial.println("\nConnecting to Wi-Fi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi connected!");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // Check if we are connected to the network
  if (WiFi.status() == WL_CONNECTED) {
    
    Serial.println("\nConnecting to Raspberry Pi server...");
    
    // Attempt to connect to the server
    if (client.connect(serverAddress, serverPort)) {
      Serial.println("Connected to server!");
      
      sendRequest(getUserInput());
      
      getResponse(timeOutPeriod);

    // Disconnect after the exchange
      client.stop();
      Serial.println("Connection closed.");
      
    } else {
      Serial.println("Connection to server failed.");
    }
  }

  // Delay before the next request (e.g., 10 seconds)
  delay(10000); 
}
