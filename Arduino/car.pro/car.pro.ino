#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Adafruit_APDS9960.h>

// --- Declarações Antecipadas de Funções ---
void escreverLCD(String msgLinha1, String msgLinha2, bool limparTela, int apenasLinha = 0);
void exibirDiagnosticoSensores();
void controlarSemaforo();
void reiniciarCiclo();
long lerUltrassonico();
void detectarGesto();
void lerCor();
void controlarMotores(int cmdEsq, int cmdDir);
void pararMotores();
void seguirLinha();
bool lerDadosRFID();
void processarDadosColetados();
void atualizarDisplayOperacional();

// --- Definições de Pinos ---
const int motorEsq_IN1 = 5;
const int motorEsq_IN2 = A0;
const int motorDir_IN3 = 6;
const int motorDir_IN4 = A3;

const int trigPin = 2;
const int echoPin = 3; 

const int sensorEsquerdaPin = A1;
const int sensorDireitaPin = A2;

const int SS_PIN = 10;
const int RST_PIN = 9;

const int ledVermelhoPin = 4;
const int ledAmareloPin = 8;   
const int ledVerdePin = 7;   

// --- Objetos Globais ---
LiquidCrystal_I2C lcd(0x27, 16, 2);
MFRC522 mfrc522(SS_PIN, RST_PIN);
Adafruit_APDS9960 apds;

// --- Variáveis de Ajuste ---
int sensibilidadeIR = 600;
int distParada = 30;
int tempoIgnoraUltra = 2500;

// --- Variáveis de Estado e Controle ---
#define SIZE_BUFFER 18
#define MAX_SIZE_BLOCK 16
MFRC522::MIFARE_Key key;
MFRC522::StatusCode statusRFID_lib;
int coletasRFID = 0;
int dadosRFID[5] = {0, 0, 0, 0, 0};
String ultimaTagLidaStr = "";
int posMaiorRFID = 0; 
int posMenorRFID = 0; 

bool ignorarUltrassonico = false;
unsigned long tempoInicioIgnorar = 0;
long distanciaAtual = 0;

uint16_t r_color, g_color, b_color, c_color;
String ultimoGesto = "---";
bool apdsDisponivel = true;
bool rfidDisponivel = true;

char statusMotorEsq = 'P';
char statusMotorDir = 'P';

#define CMD_MOTOR_PARAR_FREIO 0 
#define CMD_MOTOR_FRENTE 1
#define CMD_MOTOR_RE    2       

enum EstadoBuscaLinha { NAO_BUSCANDO, BUSCANDO_DIREITA, BUSCANDO_ESQUERDA, BUSCA_CONCLUIDA_SEM_SUCESSO };
EstadoBuscaLinha estadoBusca = NAO_BUSCANDO;
unsigned long tempoInicioBusca = 0;
const int DURACAO_GIRO_BUSCA = 2000;

enum EstadoRobo {
  INICIALIZANDO, SEGUINDO_LINHA, PARADO_OBSTACULO, LENDO_RFID,
  PROCESSANDO_DADOS, AGUARDANDO_GESTO, PARADA_EMERGENCIA,
  DIAGNOSTICO_SENSORES
};
EstadoRobo estadoAtual = INICIALIZANDO;
String msgLcdLinha1Anterior = "";
String msgLcdLinha2Anterior = "";

int paginaDiagnostico = 0;
unsigned long tempoUltimaMudancaPagina = 0;
const int intervaloMudancaPagina = 3500;


void setup() {
  Serial.begin(9600);
  lcd.init();
  lcd.backlight();
  escreverLCD("INICIANDO SYS...", "", true);

  pinMode(motorEsq_IN1, OUTPUT); pinMode(motorEsq_IN2, OUTPUT);
  pinMode(motorDir_IN3, OUTPUT); pinMode(motorDir_IN4, OUTPUT);
  pararMotores();

  pinMode(trigPin, OUTPUT); pinMode(echoPin, INPUT);
  pinMode(sensorEsquerdaPin, INPUT); pinMode(sensorDireitaPin, INPUT);

  pinMode(ledVermelhoPin, OUTPUT); pinMode(ledAmareloPin, OUTPUT); pinMode(ledVerdePin, OUTPUT);
  digitalWrite(ledVermelhoPin, LOW); digitalWrite(ledAmareloPin, LOW); digitalWrite(ledVerdePin, LOW);
  
  SPI.begin();
  mfrc522.PCD_Init();
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;
  
  byte versaoRFID = mfrc522.PCD_ReadRegister(MFRC522::VersionReg);
  if (versaoRFID == 0x00 || versaoRFID == 0xFF) {
      Serial.println("RFID MFRC522 Falha!");
      rfidDisponivel = false;
  } else {
      Serial.print("RFID Ver:0x"); Serial.println(versaoRFID, HEX);
      rfidDisponivel = true;
  }
  escreverLCD(rfidDisponivel ? "RFID OK" : "RFID FALHA", "", false, 2); // Escreve na linha 2 (índice 1)
  delay(1000);

  if (!apds.begin()) {
    Serial.println("Falha APDS9960! Gestos/Cor OFF.");
    escreverLCD("ERRO APDS", "Gestos OFF", true); // Limpa e escreve
    apdsDisponivel = false;
    delay(2000); 
  } else {
    apdsDisponivel = true;
    apds.enableColor(true); apds.enableGesture(true);
    Serial.println("APDS9960 Pronto.");
    escreverLCD("APDS OK", rfidDisponivel ? "RFID OK" : "RFID FALHA", false); // Reescreve ambas as linhas
    delay(1000);
  }

  if (estadoAtual != PARADA_EMERGENCIA) {
    if (apdsDisponivel) {
      escreverLCD("ROBO PRONTO!", "Aguard. Gesto", true);
      estadoAtual = AGUARDANDO_GESTO;
    } else {
      escreverLCD("APDS FALHOU", "Iniciando Linha", true);
      delay(1500);
      estadoAtual = SEGUINDO_LINHA;
    }
  }
  controlarSemaforo();
}

void loop() {
  distanciaAtual = lerUltrassonico();
  detectarGesto(); 
  lerCor(); 

  if (estadoAtual != DIAGNOSTICO_SENSORES) {
    atualizarDisplayOperacional();
  }
  
  if (ignorarUltrassonico && (millis() - tempoInicioIgnorar > tempoIgnoraUltra)) {
    ignorarUltrassonico = false;
    if (estadoAtual == PARADO_OBSTACULO && coletasRFID < 5) estadoAtual = SEGUINDO_LINHA;
  }

  switch (estadoAtual) {
    case INICIALIZANDO: break;
    case SEGUINDO_LINHA:
      if (distanciaAtual <= distParada && !ignorarUltrassonico) {
        pararMotores(); estadoAtual = PARADO_OBSTACULO;
      } else seguirLinha();
      break;
    case PARADO_OBSTACULO:
      pararMotores();
      if (coletasRFID < 5) estadoAtual = LENDO_RFID;
      else estadoAtual = PROCESSANDO_DADOS;
      break;
    case LENDO_RFID:
      pararMotores();
      if (!rfidDisponivel) {
        ignorarUltrassonico = true; tempoInicioIgnorar = millis();
        estadoAtual = SEGUINDO_LINHA; 
      } else {
        if (lerDadosRFID()) {
          delay(500); 
          coletasRFID++;
          ignorarUltrassonico = true; tempoInicioIgnorar = millis();
          if (coletasRFID >= 5) estadoAtual = PROCESSANDO_DADOS;
          else if (distanciaAtual > distParada || ignorarUltrassonico) estadoAtual = SEGUINDO_LINHA;
          else estadoAtual = PARADO_OBSTACULO;
        } else {
            if (distanciaAtual > distParada && !ignorarUltrassonico) estadoAtual = SEGUINDO_LINHA;
        }
      }
      break;
    case PROCESSANDO_DADOS:
      pararMotores();
      processarDadosColetados();
      if (apdsDisponivel) {
          estadoAtual = AGUARDANDO_GESTO;
          // A mensagem no LCD será atualizada por atualizarDisplayOperacional ou pela entrada no estado
      } else {
          escreverLCD("FIM DO CICLO", "Reiniciando...", true);
          delay(3000);
          reiniciarCiclo(); 
      }
      break;
    case AGUARDANDO_GESTO:
      pararMotores();
      if (apdsDisponivel) {
        if (ultimoGesto == "CIMA") reiniciarCiclo();
        else if (ultimoGesto == "BAIXO") { estadoAtual = PARADA_EMERGENCIA; }
        else if (ultimoGesto == "ESQUERDA") {
            estadoAtual = DIAGNOSTICO_SENSORES;
            paginaDiagnostico = 0; tempoUltimaMudancaPagina = millis();
            escreverLCD("MODO DIAGN.", "DIR. p/ Sair", true); delay(1000); 
        }
        if(ultimoGesto != "---" && ultimoGesto != "N/A") ultimoGesto = "---";
      } // Se APDS não disponível, display já informa "Gestos OFF" via atualizarDisplayOperacional
      break;
    case DIAGNOSTICO_SENSORES:
      pararMotores(); 
      exibirDiagnosticoSensores(); 
      if (apdsDisponivel && ultimoGesto == "DIREITA") {
        estadoAtual = AGUARDANDO_GESTO; ultimoGesto = "---";
      } else if (!apdsDisponivel && millis() - tempoUltimaMudancaPagina > 20000 && paginaDiagnostico == 4) { // Timeout de 20s na última página se APDS falhou
        estadoAtual = SEGUINDO_LINHA; 
      }
      break;
    case PARADA_EMERGENCIA:
      pararMotores();
      escreverLCD("PARADA EMERG.", ultimoGesto == "BAIXO" ? "Gesto BAIXO" : "ERRO SISTEMA", true);
      break;
  }
  controlarSemaforo(); 
  delay(50); 
}

void atualizarDisplayOperacional(){
  String l1 = "D:" + String(distanciaAtual);
  bool esqNaLinha = (analogRead(sensorEsquerdaPin) < sensibilidadeIR);
  bool dirNaLinha = (analogRead(sensorDireitaPin) < sensibilidadeIR);
  l1 += " E" + String(esqNaLinha ? 'S' : 'N'); 
  l1 += " D" + String(dirNaLinha ? 'S' : 'N');
  
  String l2 = "M:" + String(statusMotorEsq) + String(statusMotorDir);
  l2 += " G:";
  if (apdsDisponivel) {
    if (ultimoGesto == "---" || ultimoGesto == "N/A") {
      l2 += "-";
    } else {
      l2 += String(ultimoGesto.charAt(0)); // Converte char para String para concatenação
    }
  } else {
    l2 += "X";
  }
  
  l2 += " R:";
  if (!rfidDisponivel) {
    l2 += "F";
  } else if (estadoAtual == LENDO_RFID && ultimaTagLidaStr.length() > 0) { // Usa .length() > 0 em vez de !isEmpty()
    l2 += "L*";
  } else if (estadoAtual == LENDO_RFID) {
    l2 += "L?";
  } else {
    l2 += "K"; 
  }
  
  escreverLCD(l1.substring(0,16), l2.substring(0,16), false);
}

void escreverLCD(String msgLinha1, String msgLinha2, bool limparTela, int apenasLinha) {
  if (limparTela) {
    lcd.clear(); msgLcdLinha1Anterior = ""; msgLcdLinha2Anterior = "";
  }
  if (apenasLinha == 0 || apenasLinha == 1) {
    if (msgLinha1 != msgLcdLinha1Anterior || limparTela) {
      lcd.setCursor(0, 0); lcd.print(msgLinha1.substring(0, 16));
      for(int i = msgLinha1.length(); i < 16; i++) lcd.print(" ");
      msgLcdLinha1Anterior = msgLinha1;
    }
  }
  if (apenasLinha == 0 || apenasLinha == 2) {
     if (msgLinha2 != msgLcdLinha2Anterior || limparTela) {
      lcd.setCursor(0, 1); lcd.print(msgLinha2.substring(0, 16));
      for(int i = msgLinha2.length(); i < 16; i++) lcd.print(" ");
      msgLcdLinha2Anterior = msgLinha2;
    }
  }
}

long lerUltrassonico() {
  digitalWrite(trigPin, LOW); delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 25000); 
  if (duration == 0) return 999;
  return duration / 58.2;
}

void controlarMotores(int cmdEsq, int cmdDir) {
  switch(cmdEsq) {
    case CMD_MOTOR_FRENTE: digitalWrite(motorEsq_IN1, HIGH); digitalWrite(motorEsq_IN2, LOW); statusMotorEsq = 'F'; break;
    case CMD_MOTOR_RE:     digitalWrite(motorEsq_IN1, LOW);  digitalWrite(motorEsq_IN2, HIGH); statusMotorEsq = 'R'; break;
    default:               digitalWrite(motorEsq_IN1, LOW);  digitalWrite(motorEsq_IN2, LOW);  statusMotorEsq = 'P'; break;
  }
  switch(cmdDir) {
    case CMD_MOTOR_FRENTE: digitalWrite(motorDir_IN3, HIGH); digitalWrite(motorDir_IN4, LOW); statusMotorDir = 'F'; break;
    case CMD_MOTOR_RE:     digitalWrite(motorDir_IN3, LOW);  digitalWrite(motorDir_IN4, HIGH); statusMotorDir = 'R'; break;
    default:               digitalWrite(motorDir_IN3, LOW);  digitalWrite(motorDir_IN4, LOW);  statusMotorDir = 'P'; break;
  }
}

void pararMotores() {
  controlarMotores(CMD_MOTOR_PARAR_FREIO, CMD_MOTOR_PARAR_FREIO);
}

void seguirLinha() {
  bool esqNaLinha = (analogRead(sensorEsquerdaPin) < sensibilidadeIR);
  bool dirNaLinha = (analogRead(sensorDireitaPin) < sensibilidadeIR);
  
  if (esqNaLinha && dirNaLinha) { 
    controlarMotores(CMD_MOTOR_FRENTE, CMD_MOTOR_FRENTE);
    estadoBusca = NAO_BUSCANDO;
  } else if (esqNaLinha && !dirNaLinha) { 
    controlarMotores(CMD_MOTOR_PARAR_FREIO, CMD_MOTOR_FRENTE); 
    estadoBusca = NAO_BUSCANDO;
  } else if (!esqNaLinha && dirNaLinha) { 
    controlarMotores(CMD_MOTOR_FRENTE, CMD_MOTOR_PARAR_FREIO);
    estadoBusca = NAO_BUSCANDO;
  } else { 
    if (estadoBusca == NAO_BUSCANDO) {
      controlarMotores(CMD_MOTOR_FRENTE, CMD_MOTOR_RE); 
      estadoBusca = BUSCANDO_DIREITA;
      tempoInicioBusca = millis();
    } else if (estadoBusca == BUSCANDO_DIREITA) {
      if (millis() - tempoInicioBusca > DURACAO_GIRO_BUSCA) {
        controlarMotores(CMD_MOTOR_RE, CMD_MOTOR_FRENTE); 
        estadoBusca = BUSCANDO_ESQUERDA;
        tempoInicioBusca = millis();
      } else controlarMotores(CMD_MOTOR_FRENTE, CMD_MOTOR_RE);
    } else if (estadoBusca == BUSCANDO_ESQUERDA) {
      if (millis() - tempoInicioBusca > DURACAO_GIRO_BUSCA) {
        pararMotores(); 
        estadoBusca = BUSCA_CONCLUIDA_SEM_SUCESSO; 
      } else controlarMotores(CMD_MOTOR_RE, CMD_MOTOR_FRENTE);
    } else if (estadoBusca == BUSCA_CONCLUIDA_SEM_SUCESSO) pararMotores();
  }
}

bool lerDadosRFID() {
  static int proximoIdUnicoCartao = 1; 
  if (!rfidDisponivel) { ultimaTagLidaStr = "RFID F"; return false; }
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) { ultimaTagLidaStr = ""; return false; }

  byte bloco = 1; 
  statusRFID_lib = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, bloco, &key, &(mfrc522.uid));
  if (statusRFID_lib != MFRC522::STATUS_OK) {
    Serial.print("RFID Auth F: "); Serial.println(mfrc522.GetStatusCodeName(statusRFID_lib));
    ultimaTagLidaStr = "Auth F"; mfrc522.PICC_HaltA(); mfrc522.PCD_StopCrypto1(); return false;
  }

  byte bufferLeitura[SIZE_BUFFER] = {0}; byte tamanhoLeitura = SIZE_BUFFER;
  statusRFID_lib = mfrc522.MIFARE_Read(bloco, bufferLeitura, &tamanhoLeitura);

  String strLida = ""; int valFinal = 0; bool gravarNovo = false;

  if (statusRFID_lib != MFRC522::STATUS_OK) {
    Serial.print("RFID Read F: "); Serial.println(mfrc522.GetStatusCodeName(statusRFID_lib)); gravarNovo = true; 
  } else {
    for (uint8_t i = 0; i < MAX_SIZE_BLOCK; i++) {
      if (isprint(bufferLeitura[i])) strLida += char(bufferLeitura[i]); else if (bufferLeitura[i] == 0) break; 
    }
    strLida.trim();
    if (strLida.length() == 0) {gravarNovo = true; Serial.println("RFID: Bloco vazio, gravando.");}
    else {
      long tempVal = strLida.toInt();
      if (tempVal == 0 && strLida != "0") {gravarNovo = true; Serial.println("RFID: Nao numerico, gravando.");}
      else if (tempVal == 0 && strLida == "0") { gravarNovo = true; Serial.println("RFID: '0' lido, gravando novo.");}
      else valFinal = tempVal;
    }
  }

  if (gravarNovo) {
    valFinal = proximoIdUnicoCartao; String strGravar = String(valFinal);
    byte bufferEscrita[MAX_SIZE_BLOCK];
    for (int i = 0; i < MAX_SIZE_BLOCK; ++i) bufferEscrita[i] = (i < strGravar.length()) ? strGravar.charAt(i) : ' ';
    statusRFID_lib = mfrc522.MIFARE_Write(bloco, bufferEscrita, MAX_SIZE_BLOCK);
    if (statusRFID_lib == MFRC522::STATUS_OK) {
      Serial.print("Gravado ID: "); Serial.println(valFinal);
      ultimaTagLidaStr = strGravar; proximoIdUnicoCartao++;
    } else {
      Serial.print("RFID Write F: "); Serial.println(mfrc522.GetStatusCodeName(statusRFID_lib));
      ultimaTagLidaStr = "Write F"; mfrc522.PICC_HaltA(); mfrc522.PCD_StopCrypto1(); return false;
    }
  } else ultimaTagLidaStr = strLida;
  
  dadosRFID[coletasRFID] = valFinal;
  mfrc522.PICC_HaltA(); mfrc522.PCD_StopCrypto1(); 
  return true;
}

void processarDadosColetados() {
  pararMotores();
  if (coletasRFID == 0) { 
    escreverLCD("Nenhum dado RFID", "", true); 
    delay(2000); return; 
  }
  escreverLCD("DESEMPILHANDO:", "", true); 
  
  int maiorVal = dadosRFID[0]; int menorVal = dadosRFID[0];
  posMaiorRFID = 0; posMenorRFID = 0;

  for (int i = 0; i < coletasRFID; i++) {
    if (dadosRFID[i] > maiorVal) { maiorVal = dadosRFID[i]; posMaiorRFID = i; }
    if (dadosRFID[i] < menorVal) { menorVal = dadosRFID[i]; posMenorRFID = i; }
  }

  lcd.setCursor(0, 1); lcd.print("                "); 
  for(int i=0; i < coletasRFID; i++){
    if (i < 5) { 
      lcd.setCursor(i * 3, 1); 
      lcd.print(dadosRFID[i]);
    }
  }
  if (posMaiorRFID < 5 && posMaiorRFID >=0) {
    int colOriginal = posMaiorRFID * 3;
    int lenNum = String(dadosRFID[posMaiorRFID]).length();
    int colMarcador = colOriginal + lenNum;
    if (colMarcador > 15) colMarcador = colOriginal + lenNum -1;
    if (colMarcador < 0) colMarcador = 0;
    lcd.setCursor(constrain(colMarcador, 0, 15), 1); lcd.print("+");
  }
  if (posMenorRFID < 5 && posMenorRFID >=0) {
    int colOriginal = posMenorRFID * 3;
    int lenNum = String(dadosRFID[posMenorRFID]).length();
    int colMarcador = colOriginal + lenNum;
    if (colMarcador > 15) colMarcador = colOriginal + lenNum -1;
    if (colMarcador < 0) colMarcador = 0;
    if (posMenorRFID == posMaiorRFID && colMarcador == ((posMaiorRFID*3)+String(dadosRFID[posMaiorRFID]).length())) colMarcador++;
    if (colMarcador < 16) { lcd.setCursor(constrain(colMarcador, 0, 15), 1); lcd.print("-"); }
  }
  delay(5000);
}

void detectarGesto() {
  if (!apdsDisponivel) { if(ultimoGesto != "N/A") ultimoGesto = "N/A"; return; }
  if (apds.gestureValid()) { 
    int gVal = apds.readGesture(); String gID = "---";
    switch (gVal) {
      case APDS9960_DOWN: gID = "BAIXO"; break; case APDS9960_UP: gID = "CIMA"; break;
      case APDS9960_LEFT: gID = "ESQUERDA"; break; case APDS9960_RIGHT: gID = "DIREITA"; break;
    }
    if(gID != "---"){ ultimoGesto = gID; }
  }
}

void lerCor() {
  if (!apdsDisponivel) return;
  if(apds.colorDataReady()){ apds.getColorData(&r_color, &g_color, &b_color, &c_color); }
}

void exibirDiagnosticoSensores() {
  if (millis() - tempoUltimaMudancaPagina > intervaloMudancaPagina) {
    paginaDiagnostico = (paginaDiagnostico + 1) % 5;
    tempoUltimaMudancaPagina = millis();
  }
  String l1 = "", l2 = "";
  bool limpar = (millis() - tempoUltimaMudancaPagina < 150); 

  switch (paginaDiagnostico) {
    case 0: l1="Linha Esq(A1):"; l2=String(analogRead(sensorEsquerdaPin)); break;
    case 1: l1="Linha Dir(A2):"; l2=String(analogRead(sensorDireitaPin)); break;
    case 2: l1="Ultrassonico:";  l2="Dist: "+String(distanciaAtual)+"cm"; break;
    case 3: 
      l1="APDS Gestos:";   
      l2 = String("Sts:") + (apdsDisponivel ? "OK" : "F!"); 
      l2 += String(" G:") + (apdsDisponivel ? ultimoGesto : "N/A"); 
      break;
    case 4: 
      l1="APDS Cor(RGB):"; 
      l2 = String("Sts:") + (apdsDisponivel ? "OK" : "F!");
      if(apdsDisponivel) l2 += String(" ") + String(r_color) + "," + String(g_color) + "," + String(b_color);
      else l2 += " N/A";
      break;
  }
  escreverLCD(l1, l2, limpar);
}

void controlarSemaforo() {
  digitalWrite(ledVermelhoPin, LOW); digitalWrite(ledAmareloPin, LOW); digitalWrite(ledVerdePin, LOW);
  switch (estadoAtual) {
    case SEGUINDO_LINHA: digitalWrite(ledVerdePin, HIGH); break;
    case PARADO_OBSTACULO: case LENDO_RFID:
      if (!rfidDisponivel && estadoAtual == LENDO_RFID) digitalWrite(ledVermelhoPin, (millis()%600 < 300) ? LOW : HIGH);
      else digitalWrite(ledAmareloPin, (millis()%1000 < 500) ? LOW : HIGH);
      break;
    case PROCESSANDO_DADOS: digitalWrite(ledAmareloPin, HIGH); break;
    case AGUARDANDO_GESTO:
      if(apdsDisponivel) digitalWrite(ledVerdePin, (millis()%2000 < 1000) ? LOW : HIGH);
      else digitalWrite(ledAmareloPin, HIGH); 
      break;
    case DIAGNOSTICO_SENSORES: 
      (millis()%1000 < 500) ? digitalWrite(ledAmareloPin, HIGH) : digitalWrite(ledVerdePin, HIGH); break;
    case PARADA_EMERGENCIA:
      digitalWrite(ledVermelhoPin, (millis()%500 < 250) ? LOW : HIGH); break;
    case INICIALIZANDO:
      digitalWrite(ledVermelhoPin, HIGH); digitalWrite(ledAmareloPin, HIGH); digitalWrite(ledVerdePin, HIGH); break;
  }
}

void reiniciarCiclo() {
    escreverLCD("REINICIANDO...", "Aguarde...", true);
    coletasRFID = 0; for(int i=0; i<5; i++) dadosRFID[i] = 0;
    ignorarUltrassonico = false; 
    if (apdsDisponivel) ultimoGesto = "---";
    estadoBusca = NAO_BUSCANDO;
    
    long distTemp = lerUltrassonico(); 
    if (distTemp <= distParada && !ignorarUltrassonico) estadoAtual = PARADO_OBSTACULO;
    else estadoAtual = SEGUINDO_LINHA;
    escreverLCD("Ciclo Reiniciado", (estadoAtual == SEGUINDO_LINHA ? "Seg. Linha" : "Obstaculo!"), false);
    delay(1000);
}
