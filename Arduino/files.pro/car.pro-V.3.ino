// Inclui as bibliotecas necessárias
#include <Wire.h>
#include <MFRC522.h>
#include <Ultrasonic.h>
#include <LiquidCrystal_I2C.h>

// Define os pinos para a ponte H
#define IN1 2
#define IN2 3
#define IN3 4
#define IN4 5

// DEFINE PINOS ANALOGICOS DO SENSOR IR lateral
#define SIR1 A0
#define SIR2 A1

// ultrasonico
#define pt 7
#define pe 6
Ultrasonic ultrasonic(pt, pe);

// Define os pinos para o semáforo
#define Y 10
#define R 10
#define G 10

// Define os pinos para o RFID-RC522
#define SS 10
#define RST 9

// Define as variaveis para o RFID-RC522
#define SIZE_BUFFER 18
#define MAX_SIZE_BLOCK 16
MFRC522 mfrc522(SS, RST);
MFRC522::MIFARE_Key key;
MFRC522::StatusCode status;

// Define o display
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Define variaveis de ajuste

int senseSIR = 700;  // sensibilidade sensor IR
int disParada = 30;  // distancia de parada
int TIgnora = 1000;  // tempo que ele vai ignorar o objeto ao lado para continuar sem ser parado pelo sensor ultrasonico apos realizar a leitura do rfid

// Define variaveis (NÃO ALTERAR)

int coletas = 0;
int guarda[5] = { 0, 0, 0, 0, 0 };  // dados pegos
bool ignora = false;
unsigned long int tempo = 0;
int maior = 0;
int menor = 100;
int pmaior = 0;
int pmenor = 0;

void setup() {
  Serial.begin(9600);

  // display
  lcd.init();
  lcd.backlight();
  escrita("INICIANDO", 0, 0);

  //RFID
  SPI.begin();
  mfrc522.PCD_Init();

  // Configura os pinos ponte h
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // Configura os pinos sensor IR
  pinMode(SIR1, INPUT);
  pinMode(SIR2, INPUT);

  //ponte h desliga
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);

  delay(5000);
  ignora = true;
  tempo = millis();
}
void loop() {
  int distancia = ultrasonic.read(CM);
  int sensor1 = analogRead(SIR1);
  int sensor2 = analogRead(SIR2);

  if (sensor1 < senseSIR && sensor2 < senseSIR && distancia > disParada or sensor1 > senseSIR && sensor2 > senseSIR && distancia > disParada or sensor1 < senseSIR && sensor2 < senseSIR && ignora == true or sensor1 > senseSIR && sensor2 > senseSIR && ignora == true) {
    digitalWrite(IN2, HIGH);
    digitalWrite(IN3, HIGH);

    escrita("EM FRENTE", 0, 0);

  } else if (sensor1 < senseSIR && sensor2 > senseSIR && distancia > disParada or sensor1 < senseSIR && sensor2 > senseSIR && ignora == true) {
    digitalWrite(IN2, HIGH);
    digitalWrite(IN3, LOW);

    escrita("DIREITA", 0, 0);

  } else if (sensor1 > senseSIR && sensor2 < senseSIR && distancia > disParada or sensor1 > senseSIR && sensor2 < senseSIR && ignora == true) {
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, HIGH);

    escrita("ESQUERDA", 0, 0);

  } else if (coletas < 5 && ignora == false) {
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    escrita("AGUARDANDO RFID", 0, 0);
    while (guarda[coletas] == 0) {
      leituraDados();
    }
    ignora = true;
    coletas++;
    tempo = millis();
  } else if (coletas >= 5) {
    escrita("DESEMPILHANDO:", 0, 0);
    digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);
    for (int o = 0; o < 5; o++) {  // marca o maior e o menor valor
      if (guarda[o] > maior) {
        maior = guarda[o];
        pmaior = o;
      }
      if (guarda[o] < menor) {
        menor = guarda[o];
        pmenor = o;
      }
      Serial.println(pmaior);
      Serial.println(pmenor);
      Serial.println();
    }
    Serial.println();
    lcd.setCursor(0, 1);
    lcd.print(guarda[0]);
    lcd.setCursor(3, 1);
    lcd.print(guarda[1]);
    lcd.setCursor(6, 1);
    lcd.print(guarda[2]);
    lcd.setCursor(9, 1);
    lcd.print(guarda[3]);
    lcd.setCursor(12, 1);
    lcd.print(guarda[4]);
    lcd.setCursor(2+(pmaior * 3), 1);
    lcd.print("+");
    lcd.setCursor(2+(pmenor * 3), 1);
    lcd.print("-");
    while (true) {
      delay(100);
    }
  }
  if (ignora == true && millis() - tempo > TIgnora) {
    ignora = false;
    tempo = millis();
  }
}

void escrita(String a, int b, int c) {
  static String altera = "";
  if (altera != a) {
    lcd.clear();
    lcd.setCursor(b, c);
    lcd.print(a);
    altera = a;
  }
}

void leituraDados() {
  if (!mfrc522.PICC_IsNewCardPresent()) {
    return;
  }
  if (!mfrc522.PICC_ReadCardSerial()) {
    return;
  }
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;
  byte buffer[SIZE_BUFFER] = { 0 };
  byte bloco = 1;
  byte tamanho = SIZE_BUFFER;
  status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, bloco, &key, &(mfrc522.uid));
  if (status != MFRC522::STATUS_OK) {
    return;
  }
  status = mfrc522.MIFARE_Read(bloco, buffer, &tamanho);
  String l = "";
  for (uint8_t i = 0; i < MAX_SIZE_BLOCK; i++) {
    l = l + char(buffer[i]);
  }
  guarda[coletas] = l.toInt();
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}
