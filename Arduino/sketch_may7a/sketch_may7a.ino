#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>

StaticJsonDocument<256> jsonDoc;

const char* ssid = "UPC3562988";
const char* password = "Sowelo8888";
const char* serverIP = "192.168.0.36";
const int serverPort = 5554;
ESP8266WebServer server(serverPort);


uint32_t personCount {0};
uint32_t waitForNextSensor1 {3500};
uint32_t waitForNextSensor2 {3500};
uint32_t waitAfterReading1 {2000};
uint32_t waitAfterReading2 {2000};
int direction {0};


constexpr uint8_t IR_PIN1 {4};
constexpr uint8_t IR_PIN2 {14};
constexpr uint8_t BLUE_LED {2};

void handleGetVar() {
  String json = String("{\"value\":")   + personCount
              + String(",\"sensor1\":") + digitalRead(IR_PIN1)
              + String(",\"sensor2\":") + digitalRead(IR_PIN2)
              + String(",\"waitForNextSensor1\":") + waitForNextSensor1
              + String(",\"waitForNextSensor2\":") + waitForNextSensor2
              + String(",\"waitAfterReading1\":") + waitAfterReading1
              + String(",\"waitAfterReading2\":") + waitAfterReading2
              + String(",\"direction\":") + direction
              + String("}");
  server.send(200, "application/json", json);
}

void handleSetVar() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"Missing body\"}");
    return;
  }

  auto err = deserializeJson(jsonDoc, server.arg("plain"));
  if (err) {
    server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
    return;
  }

  if (jsonDoc.containsKey("value")) {
    personCount = jsonDoc["value"].as<uint32_t>();
  }
  if (jsonDoc.containsKey("waitForNextSensor1")) {
    waitForNextSensor1 = jsonDoc["waitForNextSensor1"].as<unsigned long>();
  }
  if (jsonDoc.containsKey("waitForNextSensor2")) {
    waitForNextSensor2 = jsonDoc["waitForNextSensor2"].as<unsigned long>();
  }
  if (jsonDoc.containsKey("waitAfterReading1")) {
    waitAfterReading1 = jsonDoc["waitAfterReading1"].as<unsigned long>();
  }
  if (jsonDoc.containsKey("waitAfterReading2")) {
    waitAfterReading2 = jsonDoc["waitAfterReading2"].as<unsigned long>();
  }
  if (jsonDoc.containsKey("direction")) {
    direction = jsonDoc["direction"].as<int>();
  }

  server.send(200, "application/json", "{\"status\":\"OK\"}");
}


bool waitFor(uint8_t pin, uint8_t state, unsigned long timeoutms) {
  unsigned long start = millis();
  while (millis() - start < timeoutms) {
    if(digitalRead(pin) == state) {
      return true;
    }
    server.handleClient();
    yield();
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(IR_PIN1, INPUT);
  pinMode(IR_PIN2, INPUT);
  pinMode(BLUE_LED, OUTPUT);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.printf("Connecting to %s", ssid);

  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  server.on("/var", HTTP_GET, handleGetVar);  
  server.on("/var", HTTP_POST, handleSetVar);  
  server.begin();

  Serial.println();
  Serial.printf("Wi-Fi connected\n");
}

void loop() {
  server.handleClient();
  digitalWrite(BLUE_LED, LOW);
  unsigned long t1, t2, d1, d2;
  if(digitalRead(IR_PIN1) == HIGH)
  {
    t1 = millis();
    digitalWrite(BLUE_LED, HIGH);
     if((waitFor(IR_PIN2, HIGH, waitForNextSensor1))){
      d1 = millis() - t1;
      //Wybieramy w ktora strone dodajemy - 0 lub cokolwiek innego
      if(direction == 0){
      if(d1 >= 10) {
      personCount = personCount + 1;
     }
      }
     else {
        if(d1 >= 10 && personCount > 0) {
      personCount = personCount - 1;
     }
     }
    waitFor(IR_PIN1, LOW, waitAfterReading1);
  }
  }
  
  else if(digitalRead(IR_PIN2) == HIGH)
  {
    t2 = millis();
    digitalWrite(BLUE_LED, HIGH);
     if((waitFor(IR_PIN1, HIGH, waitForNextSensor2))){
      d2 = millis() - t2;
      //Wybieramy w ktora strone dodajemy - 0 lub cokolwiek innego
      if (direction == 0){
      if(d2 >= 10 && personCount > 0) {
      personCount--;
     }
      }
     else {
      if(d2 >= 10) {
      personCount++;
     }
     }
     }

    waitFor(IR_PIN2, LOW, waitAfterReading2);
  }

  }
