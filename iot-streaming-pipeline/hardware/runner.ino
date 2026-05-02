#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <LittleFS.h>
#include <ArduinoOTA.h>
#include "mbedtls/md.h" 
#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>
#include <time.h> 
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h> 

const char* ssid = "Orange-C07A";
const char* password = "3D9A8721564";
const char* mqtt_server = "192.168.1.155";
const int mqtt_port = 1883; 
const char* mqtt_base_topic = "factory/line1/telemetry/"; 

// NTP Server Settings
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 3600; 
const int   daylightOffset_sec = 0;

WiFiClient espClient; 
PubSubClient client(espClient);

#define TFT_SCLK 6
#define TFT_MOSI 7
#define TFT_CS   18
#define TFT_DC   11
#define TFT_RST  10

#define MQ_PIN 1      
#define BUZZER_PIN 2  
#define POT_PIN 3     
#define RELAY_PIN 5   

#define I2C_SDA 8
#define I2C_SCL 9
Adafruit_BME280 bme; 

Adafruit_GC9A01A tft(TFT_CS, TFT_DC, TFT_MOSI, TFT_SCLK, TFT_RST);

const int GAS_DANGER_THRESHOLD = 1000;
const char* bufferFile = "/data_buffer.txt";
bool isAlarmActive = false;

struct SensorData {
  char metricName[32];
  float value;
  char timestamp[32]; 
};

QueueHandle_t telemetryQueue; 

void getProfessionalTimestamp(char* buffer, size_t maxLen) {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo, 10)) { 
    sprintf(buffer, "%lu", millis());
    return;
  }
  strftime(buffer, maxLen, "%Y-%m-%d %H:%M:%S", &timeinfo);
}

String generateHash(String payload) {
  byte shaResult[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;
  
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 0);
  mbedtls_md_starts(&ctx);
  mbedtls_md_update(&ctx, (const unsigned char *) payload.c_str(), payload.length());
  mbedtls_md_finish(&ctx, shaResult);
  mbedtls_md_free(&ctx);
  
  String hashStr = "";
  for(int i = 0; i < sizeof(shaResult); i++) {
    char str[3];
    sprintf(str, "%02x", (int)shaResult[i]);
    hashStr += str;
  }
  return hashStr;
}

bool isValidAnalog(int val) { return (val >= 0 && val <= 4095); }

void setup() {
  Serial.begin(115200);
  delay(500); 

  pinMode(MQ_PIN, INPUT);
  pinMode(POT_PIN, INPUT); 
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); 
  digitalWrite(BUZZER_PIN, LOW); 

  if (!LittleFS.begin(true)) Serial.println("FS Mount Failed!");

  Wire.begin(I2C_SDA, I2C_SCL);
  if (!bme.begin(0x77, &Wire)) { 
    Serial.println("BME280 Initialization Failed! Check Wiring or switch to BMP280 library.");
  }

  tft.begin();
  tft.setRotation(0);
  tft.fillScreen(GC9A01A_BLACK);
  tft.setTextColor(GC9A01A_CYAN);
  tft.setTextSize(3);
  tft.setCursor(40, 100);
  tft.print("SYS BOOT...");
  delay(1000); 
  tft.fillScreen(GC9A01A_BLACK); 

  WiFi.mode(WIFI_STA);
  client.setServer(mqtt_server, mqtt_port);
  ArduinoOTA.begin();

  telemetryQueue = xQueueCreate(50, sizeof(SensorData)); 

  xTaskCreate(SensorSafetyTask, "SensorTask", 4096, NULL, 2, NULL);
  xTaskCreate(NetworkCryptoTask, "NetworkTask", 8192, NULL, 1, NULL);
}

void loop() {
  vTaskDelay(portMAX_DELAY); 
}

void SensorSafetyTask(void *pvParameters) {
  int telemetryCounter = 0;
  unsigned long lastDisplayTime = 0;

  for (;;) { 
    int currentGas = analogRead(MQ_PIN);
    int currentBarrage = map(analogRead(POT_PIN), 0, 4095, 0, 100);
    float currentTemp = bme.readTemperature();
    float currentHum = bme.readHumidity(); 
    float currentPres = bme.readPressure() / 100.0F; 

    char timestampBuf[32];
    getProfessionalTimestamp(timestampBuf, sizeof(timestampBuf));

    if (currentGas > GAS_DANGER_THRESHOLD) {
      digitalWrite(RELAY_PIN, LOW);   
      digitalWrite(BUZZER_PIN, HIGH); 
      if (!isAlarmActive) {
        tft.fillScreen(GC9A01A_RED);
        tft.setTextColor(GC9A01A_WHITE);
        tft.setTextSize(4);
        tft.setCursor(45, 100);
        tft.print("ALARM!");
        isAlarmActive = true;
      }
    } else {
      digitalWrite(RELAY_PIN, HIGH); 
      digitalWrite(BUZZER_PIN, LOW); 
      if (isAlarmActive) {
        tft.fillScreen(GC9A01A_BLACK);
        isAlarmActive = false;
        lastDisplayTime = 0; 
      }
    }

    if (!isAlarmActive && (millis() - lastDisplayTime >= 2000)) {
      lastDisplayTime = millis();
      
      tft.setTextSize(2);
      char displayBuffer[32];

      tft.setTextColor(GC9A01A_GREEN, GC9A01A_BLACK);
      tft.setCursor(45, 50);
      snprintf(displayBuffer, sizeof(displayBuffer), "VOC: %-4d", currentGas);
      tft.print(displayBuffer);
      
      tft.setTextColor(GC9A01A_ORANGE, GC9A01A_BLACK);
      tft.setCursor(25, 95);
      snprintf(displayBuffer, sizeof(displayBuffer), "%-4.1fC ", currentTemp);
      tft.print(displayBuffer);
      
      tft.setTextColor(GC9A01A_CYAN, GC9A01A_BLACK);
      tft.setCursor(120, 95);
      snprintf(displayBuffer, sizeof(displayBuffer), "%-3.0f%% RH", currentHum);
      tft.print(displayBuffer);

      tft.setTextColor(GC9A01A_WHITE, GC9A01A_BLACK);
      tft.setCursor(35, 140);
      snprintf(displayBuffer, sizeof(displayBuffer), "P: %-6.1f", currentPres);
      tft.print(displayBuffer);
      
      tft.setTextColor(GC9A01A_MAGENTA, GC9A01A_BLACK);
      tft.setCursor(40, 175);
      snprintf(displayBuffer, sizeof(displayBuffer), "Vanne: %-3d%%", currentBarrage);
      tft.print(displayBuffer);
    }

    telemetryCounter++;
    if (telemetryCounter >= 20) { 
      SensorData data;
      strcpy(data.timestamp, timestampBuf);

      if (isValidAnalog(currentGas)) {
        strcpy(data.metricName, "voc_gas_raw");
        data.value = currentGas;
        xQueueSend(telemetryQueue, &data, 0);
      }
      
      if (currentBarrage >= 0 && currentBarrage <= 100) {
        strcpy(data.metricName, "barrage_valve_percent");
        data.value = currentBarrage;
        xQueueSend(telemetryQueue, &data, 0);
      }

      if (!isnan(currentTemp)) {
        strcpy(data.metricName, "tah/temperature");
        data.value = currentTemp;
        xQueueSend(telemetryQueue, &data, 0);
      }
      
      if (!isnan(currentHum) && currentHum > 0) {
        strcpy(data.metricName, "tah/humidity");
        data.value = currentHum;
        xQueueSend(telemetryQueue, &data, 0);
      }

      if (!isnan(currentPres) && currentPres > 0) {
        strcpy(data.metricName, "tah/pressure");
        data.value = currentPres;
        xQueueSend(telemetryQueue, &data, 0);
      }
      
      telemetryCounter = 0;
    }

    vTaskDelay(pdMS_TO_TICKS(50)); 
  }
}

void NetworkCryptoTask(void *pvParameters) {
  SensorData receivedData;
  bool timeConfigured = false;

  WiFi.begin(ssid, password);

  for (;;) { 
    ArduinoOTA.handle();
    
    if (WiFi.status() != WL_CONNECTED) {
      timeConfigured = false; 
      WiFi.disconnect();
      WiFi.begin(ssid, password);
      vTaskDelay(pdMS_TO_TICKS(4000)); 
      continue; 
    }

    if (!timeConfigured) {
      configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
      timeConfigured = true;
    }

    if (!client.connected()) {
       if (client.connect("ESP32_EdgeNode_C6")) {
         flushBuffer();
       } else {
         vTaskDelay(pdMS_TO_TICKS(2000));
         continue;
       }
    }
    client.loop();

    if (xQueueReceive(telemetryQueue, &receivedData, pdMS_TO_TICKS(10)) == pdTRUE) {
      
      StaticJsonDocument<256> dataDoc;
      dataDoc["timestamp"] = String(receivedData.timestamp); 
      dataDoc["site_id"] = "Factory_Line_A";
      dataDoc["metric"] = String(receivedData.metricName);
      dataDoc["value"] = receivedData.value;

      String rawDataString;
      serializeJson(dataDoc, rawDataString);
      String dataHash = generateHash(rawDataString);

      StaticJsonDocument<384> finalDoc;
      finalDoc["payload"] = dataDoc;
      finalDoc["sha256_signature"] = dataHash;

      char jsonBuffer[384];
      serializeJson(finalDoc, jsonBuffer);

      String targetTopic = String(mqtt_base_topic) + String(receivedData.metricName);

      if (client.connected()) {
        client.publish(targetTopic.c_str(), jsonBuffer);
      } else {
        saveToBuffer(jsonBuffer);
      }
    }
    
    vTaskDelay(pdMS_TO_TICKS(10)); 
  }
}

void saveToBuffer(const char* data) {
  File file = LittleFS.open(bufferFile, FILE_APPEND);
  if (file) {
    file.println(data);
    file.close();
  }
}

void flushBuffer() {
  File file = LittleFS.open(bufferFile, FILE_READ);
  if (!file) return;
  
  while (file.available()) {
    String payload = file.readStringUntil('\n');
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, payload);
    
    if (!error && doc["payload"]["metric"]) {
      String savedMetricName = doc["payload"]["metric"].as<String>();
      String targetTopic = String(mqtt_base_topic) + savedMetricName;
      
      client.publish(targetTopic.c_str(), payload.c_str());
    }
    vTaskDelay(pdMS_TO_TICKS(50)); 
  }
  file.close();
  LittleFS.remove(bufferFile); 
}