#include <Arduino.h>

// ===== MOTORS =====
// Izquierdo
const int RPWM_IZQ = 10;
const int LPWM_IZQ = 5;

// Derecho
const int RPWM_DER = 6;
const int LPWM_DER = 9;

// ===== ENCODERS =====
const int ENC_L_A = 2;
const int ENC_L_B = 7;
const int ENC_R_A = 3;
const int ENC_R_B = 8;

volatile long left_ticks = 0;
volatile long right_ticks = 0;

unsigned long last_time = 0;

// ===== ENCODER ISR =====
void leftEncoderISR() {
  if (digitalRead(ENC_L_A) == digitalRead(ENC_L_B)) left_ticks++;
  else left_ticks--;
}

void rightEncoderISR() {
  if (digitalRead(ENC_R_A) == digitalRead(ENC_R_B)) right_ticks++;
  else right_ticks--;
}

// ===== MOTOR CONTROL =====
void avanzar(int v) {
  analogWrite(RPWM_IZQ, v);
  analogWrite(LPWM_IZQ, 0);

  analogWrite(RPWM_DER, v);
  analogWrite(LPWM_DER, 0);
}

void atras(int v) {
  analogWrite(RPWM_IZQ, 0);
  analogWrite(LPWM_IZQ, v);

  analogWrite(RPWM_DER, 0);
  analogWrite(LPWM_DER, v);
}

void giraDerecha(int v) {
  analogWrite(RPWM_IZQ, v);
  analogWrite(LPWM_IZQ, 0);

  analogWrite(RPWM_DER, 0);
  analogWrite(LPWM_DER, v);
}

void parar() {
  analogWrite(RPWM_IZQ, 0);
  analogWrite(LPWM_IZQ, 0);
  analogWrite(RPWM_DER, 0);
  analogWrite(LPWM_DER, 0);
}

// ===== SERIAL PARSER =====
String buffer = "";

void processCommand(String cmd) {
  Serial.print("RECIBIDO: ");
  Serial.println(cmd);

  cmd.trim();

  if (!cmd.startsWith("CMD,")) {
    Serial.println("ERROR: formato");
    return;
  }

  cmd.remove(0, 4);

  int first = cmd.indexOf(',');
  String action = "";
  int speed = 250;

  if (first != -1) {
    action = cmd.substring(0, first);
    String speedStr = cmd.substring(first + 1);
    speedStr.trim();
    speed = speedStr.toInt();
  } else {
    action = cmd; // Por si se envía sin velocidad
  }

  action.trim(); // Asegura que "STOP" no sea "STOP " o "STOP\r"

  if (action == "AVANZA") {
    avanzar(speed);
    Serial.println("ACK,AVANZA");
  }
  else if (action == "ATRAS") {
    atras(speed);
    Serial.println("ACK,ATRAS");
  }
  else if (action == "GIRO_DER") {
    giraDerecha(speed);
    Serial.println("ACK,GIRO_DER");
  }
  else if (action == "STOP") {
    parar();
    Serial.println("ACK,STOP");
  }
  else {
    // Avisar en la terminal si llegó algo deformado
    Serial.print("ERROR,COMANDO_DESCONOCIDO:");
    Serial.println(action);
  }
}

// ===== SETUP =====
void setup() {
  Serial.begin(115200);

  pinMode(RPWM_IZQ, OUTPUT);
  pinMode(LPWM_IZQ, OUTPUT);
  pinMode(RPWM_DER, OUTPUT);
  pinMode(LPWM_DER, OUTPUT);

  pinMode(ENC_L_A, INPUT_PULLUP);
  pinMode(ENC_L_B, INPUT_PULLUP);
  pinMode(ENC_R_A, INPUT_PULLUP);
  pinMode(ENC_R_B, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENC_L_A), leftEncoderISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_R_A), rightEncoderISR, CHANGE);

  parar();
  last_time = millis();
}

// ===== LOOP =====
void loop() {

  // --- SERIAL COMMANDS ---
  if (Serial.available() > 0) {
    buffer = Serial.readStringUntil('\n');
    processCommand(buffer);
  }

  // --- ENCODERS STREAM ---
  unsigned long now = millis();
  if (now - last_time >= 20) { // 50Hz

    noInterrupts();
    long l = left_ticks;
    long r = right_ticks;
    interrupts();

    Serial.print("ENC,");
    Serial.print(l);
    Serial.print(",");
    Serial.print(r);
    Serial.print(",");
    Serial.println(now - last_time);

    last_time = now;
  }
}
