const int motorEsq_IN1 = 5;
const int motorEsq_IN2 = A0;
const int motorDir_IN3 = 6;
const int motorDir_IN4 = A3;

const int sensorEsquerdaPin = A1;
const int sensorDireitaPin = A2;

void setup() {
  Serial.begin(9600);
  pinMode(motorEsq_IN1, OUTPUT);
  pinMode(motorEsq_IN2, OUTPUT);
  pinMode(motorDir_IN3, OUTPUT);
  pinMode(motorDir_IN4, OUTPUT);
}

void controlarMotor(int pin1, int pin2, int velocidade) {
  analogWrite(pin1, velocidade);
  digitalWrite(pin2, LOW);
}

void loop() {
  // Leitura dos sensores
  int esq = analogRead(sensorEsquerdaPin);
  int dir = analogRead(sensorDireitaPin);
  
  Serial.print("Sensor Esq: ");
  Serial.print(esq);
  Serial.print(" | Dir: ");
  Serial.println(dir);

  // Controle dos motores baseado nos sensores
  if(esq < 500 && dir < 500) {       // Ambos na linha
    controlarMotor(motorEsq_IN1, motorEsq_IN2, 200);
    controlarMotor(motorDir_IN3, motorDir_IN4, 200);
  } 
  else if(esq < 500 && dir >= 500) { // Só esquerda na linha
    controlarMotor(motorEsq_IN1, motorEsq_IN2, 100);
    controlarMotor(motorDir_IN3, motorDir_IN4, 0);
  } 
  else if(esq >= 500 && dir < 500) { // Só direita na linha
    controlarMotor(motorEsq_IN1, motorEsq_IN2, 0);
    controlarMotor(motorDir_IN3, motorDir_IN4, 100);
  } 
  else {                             // Fora da linha
    analogWrite(motorEsq_IN1, 0);
    analogWrite(motorDir_IN3, 0);
  }
  
  delay(100);
}
