#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>
#include <time.h>

#define DHT_PIN   15
#define TRIG_PIN  5
#define ECHO_PIN  18
#define LED_PIN   2

const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

const char* MQTT_SERVER   = "broker.hivemq.com";
const int   MQTT_PORT     = 1883;
const char* DEVICE_ID     = "ESP32-B24DCVN086";
const char* MQTT_TOPIC    = "lab2_B24DCVN086/esp32/telemetry";

const unsigned long PUBLISH_INTERVAL = 5000;

WiFiClient espClient;
PubSubClient mqttClient(espClient);
DHTesp dht;

unsigned long lastPublish = 0;
unsigned long sequenceNumber = 0;

const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 7 * 3600;
const int   daylightOffset_sec = 0;

void connectWiFi() {
  Serial.println("\n[WIFI] Connecting to WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, 6);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WIFI] Connected!");
    Serial.print("[WIFI] IP: ");
    Serial.println(WiFi.localIP());
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  } else {
    Serial.println("\n[WIFI] Connection failed. Retrying...");
  }
}

void connectMQTT() {
  while (!mqttClient.connected()) {
    String clientId = "ESP32-WOKWI-B24DCVN086-" + String(random(0xffff), HEX);
    Serial.print("[MQTT] Connecting to broker with Client ID: ");
    Serial.println(clientId);

    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("[MQTT] Connected to HiveMQ Broker!");
    } else {
      Serial.print("[MQTT] Failed, state = ");
      Serial.println(mqttClient.state());
      delay(2000);
    }
  }
}

float readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) {
    return -1.0;
  }
  return duration * 0.0343 / 2.0;
}

unsigned long getEpochTime() {
  time_t now;
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return millis() / 1000;
  }
  time(&now);
  return (unsigned long)now;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  dht.setup(DHT_PIN, DHTesp::DHT22);

  connectWiFi();

  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
  mqttClient.setBufferSize(512);

  connectMQTT();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!mqttClient.connected()) {
    connectMQTT();
  }

  mqttClient.loop();

  unsigned long currentMillis = millis();
  if (currentMillis - lastPublish < PUBLISH_INTERVAL) {
    return;
  }
  lastPublish = currentMillis;

  TempAndHumidity data = dht.getTempAndHumidity();
  float temperature = data.temperature;
  float humidity    = data.humidity;
  float distance    = readDistance();

  bool sensorError = false;

  if (isnan(temperature) || isnan(humidity)) {
    sensorError = true;
  }
  if (!isnan(temperature) && (temperature < -40.0 || temperature > 80.0)) {
    sensorError = true;
  }
  if (!isnan(humidity) && (humidity < 0.0 || humidity > 100.0)) {
    sensorError = true;
  }
  if (distance < 2.0 || distance > 400.0) {
    sensorError = true;
  }

  if (sensorError) {
    Serial.println("[ERROR] Invalid sensor readings. Skipped publish.");
    return;
  }

  sequenceNumber++;
  unsigned long uptime = millis() / 1000;
  int rssi = WiFi.RSSI();
  unsigned long timestamp = getEpochTime();

  char payload[350];
  snprintf(
    payload,
    sizeof(payload),
    "{"
      "\"device_id\":\"%s\","
      "\"sequence\":%lu,"
      "\"uptime_s\":%lu,"
      "\"timestamp\":%lu,"
      "\"rssi\":%d,"
      "\"temperature\":%.2f,"
      "\"humidity\":%.2f,"
      "\"distance_cm\":%.2f"
    "}",
    DEVICE_ID,
    sequenceNumber,
    uptime,
    timestamp,
    rssi,
    temperature,
    humidity,
    distance
  );

  Serial.println("\n------------------------------------------");
  Serial.print("Sequence: #"); Serial.println(sequenceNumber);
  Serial.print("Temp: "); Serial.print(temperature); Serial.println(" C");
  Serial.print("Hum:  "); Serial.print(humidity); Serial.println(" %");
  Serial.print("Dist: "); Serial.print(distance); Serial.println(" cm");
  Serial.print("Payload: "); Serial.println(payload);

  bool published = mqttClient.publish(MQTT_TOPIC, payload);
  if (published) {
    Serial.println("[MQTT] Publish Success");
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
  } else {
    Serial.println("[MQTT] Publish Failed");
  }
}
