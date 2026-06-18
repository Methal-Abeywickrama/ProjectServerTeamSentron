#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "Mushab";
const char* password = "mushab123";
const char* mqttServer = "192.168.43.49";
const uint16_t mqttPort = 1883;

// --- Unique Slave Configuration ---
const String myLockerAddress = "001"; // Change this for locker 002, 003, etc.
const String myTopic = "lockers/" + myLockerAddress + "/command";

// --- Hardware Pins ---
const int SOLENOID_PIN = 4; // GPIO connected to your relay/MOSFET
const int UNLOCK_DURATION = 3000; // How long the solenoid stays open (ms)

WiFiClient espClient;
PubSubClient mqttClient(espClient);

void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

// Triggers when a message arrives on the subscribed topic
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  if (message == "OPEN") {
    Serial.println("Unlock command received. Activating solenoid...");
    
    // Actuate Solenoid
    digitalWrite(SOLENOID_PIN, HIGH);
    delay(UNLOCK_DURATION); 
    digitalWrite(SOLENOID_PIN, LOW);
    
    Serial.println("Solenoid deactivated. Locker locked.");
  }
}

void reconnect_mqtt() {
  while (!mqttClient.connected()) {
    String clientId = "SlaveLocker-" + myLockerAddress;
    if (mqttClient.connect(clientId.c_str())) {
      // Subscribe to this specific locker's command topic
      mqttClient.subscribe(myTopic.c_str());
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(SOLENOID_PIN, OUTPUT);
  digitalWrite(SOLENOID_PIN, LOW); // Ensure locked state on boot
  
  setup_wifi();
  mqttClient.setServer(mqttServer, mqttPort);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  if (!mqttClient.connected()) {
    reconnect_mqtt();
  }
  mqttClient.loop();
}