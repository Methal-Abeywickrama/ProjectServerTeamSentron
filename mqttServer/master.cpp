#include <WiFi.h>
#include <PubSubClient.h>
#include <queue> // C++ Standard Template Library for the buffer

// --- Credentials & Settings ---
const char* ssid = "Mushab";
const char* password = "mushab123";

// Raspberry Pi Details
const char* tcpServer = "192.168.43.49";
const uint16_t tcpPort = 5555;
const char* mqttServer = "192.168.43.49";
const uint16_t mqttPort = 1883;

// --- Surge Prevention Buffer ---
std::queue<String> unlockQueue;
unsigned long lastUnlockTime = 0;
const unsigned long SURGE_COOLDOWN = 2000; // 2 seconds between opening lockers

WiFiClient espClient;
PubSubClient mqttClient(espClient);

void setup_wifi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
}

void reconnect_mqtt() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect("MasterLockerClient")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

// Re-using your TCP validation logic
bool validateWithServer(String lockerAddress, String ID) {
  WiFiClient tcpClient;
  if (!tcpClient.connect(tcpServer, tcpPort)) {
    Serial.println("TCP Connection failed");
    return false;
  }
  
  String message = "GET " + lockerAddress + " MTCH " + ID;
  tcpClient.println(message);
  
  long startTime = millis();
  while (tcpClient.available() == 0) {
    if (millis() - startTime > 5000) {
      Serial.println("TCP Timeout");
      tcpClient.stop();
      return false;
    }
  }
  
  String reply = tcpClient.readStringUntil('\n');
  reply.trim();
  tcpClient.stop();

  if (reply.substring(0, 2) == "OK") {
    return true; // Authentication successful
  }
  return false;
}

// Simulating an RFID scan event
void handleRFIDScan(String lockerAddress, String scannedID) {
  Serial.println("Authenticating card: " + scannedID + " for locker " + lockerAddress);
  if (validateWithServer(lockerAddress, scannedID)) {
    Serial.println("Access Granted. Adding to unlock queue.");
    unlockQueue.push(lockerAddress); // Push to the buffer
  } else {
    Serial.println("Access Denied.");
  }
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  mqttClient.setServer(mqttServer, mqttPort);
}

void loop() {
  if (!mqttClient.connected()) {
    reconnect_mqtt();
  }
  mqttClient.loop();

  // --- Queue Processing Logic ---
  // If the queue has items AND the cooldown period has passed
  if (!unlockQueue.empty() && (millis() - lastUnlockTime >= SURGE_COOLDOWN)) {
    
    // 1. Get the next locker address from the front of the queue
    String targetLocker = unlockQueue.front();
    
    // 2. Remove it from the queue
    unlockQueue.pop(); 
    
    // 3. Construct the specific MQTT topic (e.g., "lockers/001/command")
    String topic = "lockers/" + targetLocker + "/command";
    
    // 4. Publish the open command
    mqttClient.publish(topic.c_str(), "OPEN");
    Serial.println("Dispatched OPEN command to: " + targetLocker);
    
    // 5. Reset the timer
    lastUnlockTime = millis();
  }

  // Example trigger: Replace this with your actual physical RFID reading logic
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input == "test") {
      // Simulating 3 simultaneous successful reads to test the buffer
      handleRFIDScan("001", "123456789012");
      handleRFIDScan("002", "123456789012");
      handleRFIDScan("003", "123456789012");
    }
  }
}