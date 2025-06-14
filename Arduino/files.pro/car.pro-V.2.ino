#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <SparkFun_APDS9960.h>

// Definições do motor
const int motorPin1 = 11;
const int motorPin2 = 10;

// Definições do sensor ultrassônico
const int trigPin = 2;
const int echoPin = 3;

// Definições do display LCD
LiquidCrystal_I2C lcd(0x27, 16, 2); 

// Definições dos sensores de linha
const int sensorEsquerda = 5;
const int sensorDireita = 6;

// Definições de distância
const long distanciaObstaculo = 30;

// Definições do sensor APDS-9960
SparkFun_APDS9960 apds;

// Variáveis para cores
uint16_t r, g;

// Declaração das funções
void exibirMensagem(String mensagem);
long lerDistanciaUltrassom();
void parar();
void moverFrente();
void corrigirEsquerda();
void corrigirDireita();
void girar360();

void setup() {
  // Inicializando os pinos do motor
  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);

  // Inicializando os pinos do sensor ultrassônico
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  // Inicializando os pinos dos sensores de linha
  pinMode(sensorEsquerda, INPUT);
  pinMode(sensorDireita, INPUT);

  // Inicializando o display LCD
  lcd.init();
  lcd.backlight();
  exibirMensagem("OLA BONITO");

  // Inicializando o sensor APDS-9960
  Wire.begin();
  if (apds.init()) {
    apds.enableLightSensor(true);
    lcd.setCursor(0, 1);
    lcd.print("OLA BONITO - Ok");
  } else {
    lcd.setCursor(0, 1);
    lcd.print("OLA BONITO - NOK");
  }
}

void loop() {
  int esquerda = digitalRead(sensorEsquerda);
  int direita = digitalRead(sensorDireita);

  // Lendo a distância do sensor ultrassônico
  long distancia = lerDistanciaUltrassom();

  // Lendo a cor do sensor APDS-9960
  apds.readRedLight(r);
  apds.readGreenLight(g);

  // Verificando a cor detectada
  if (r > 200 && g < 100) {
    // Cor vermelha detectada
    exibirMensagem("PARE");
    parar();
    return;
  } else if (r < 100 && g > 200) {
    // Cor verde detectada
    exibirMensagem("CONTINUE");
  }

  // Verificando a distância do obstáculo
  if (distancia <= distanciaObstaculo) {
    exibirMensagem("Obstaculo");
    parar();
    return;
  } else {
    exibirMensagem("Continuar");
  }

  // Verificando a linha
  if (esquerda == HIGH && direita == HIGH) {
    moverFrente();
  } else if (esquerda == LOW && direita == HIGH) {
    corrigirEsquerda();
  } else if (esquerda == HIGH && direita == LOW) {
    corrigirDireita();
  } else if (esquerda == LOW && direita == HIGH) {
    girar360();
  }

  delay(50); // Atraso para estabilidade
}

void moverFrente() {
  digitalWrite(motorPin1, HIGH);
  digitalWrite(motorPin2, HIGH);
}

void corrigirEsquerda() {
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);
  delay(50); // Ajuste na direção
  parar();
}

void corrigirDireita() {
  digitalWrite(motorPin1, HIGH);
  digitalWrite(motorPin2, LOW);
  delay(50); // Ajuste na direção
  parar();
}

void parar() {
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, LOW);
}

void girar360() {
  digitalWrite(motorPin1, LOW);
  digitalWrite(motorPin2, HIGH);
  delay(100);
  parar();
}

long lerDistanciaUltrassom() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(3);
  digitalWrite(trigPin, LOW);
  long duracao = pulseIn(echoPin, HIGH);
  long distancia = duracao * 0.034 / 2;
  return distancia;
}

void exibirMensagem(String mensagem) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(mensagem);
}#include <Ultrasonic.h> // biblioteca do sensor ultrasonico
#define ma 9  //Pino Velocidade 1º Motor ( 0 a 255)
#define mb 11 //Pino_Velocidade 2º Motor ( 0 a 255)
#define da 8  //Pino_Direção do 1º Motor (HIGH ou LOW)
#define db 10 //Pino_Direção do 2º Motor (HIGH ou LOW)
#define sa 6  //Pino_Sensor 1 
#define sb 5  //Pino_Sensor 2
#define pt 4  //Pino_Trigger
#define pe 3  //Pino_Echo
int d;        //Variavel valor medido do sensor
int v = 200;  //velocidade dos motores

unsigned long t = millis();  // tempo desde a ligação do arduino
Ultrasonic ultrasonic(pt, pe); // inicia sensor ultrasonico
void setup() {
  pinMode(LED_BUILTIN, OUTPUT); //define o led do arduino como saida.
  digitalWrite(LED_BUILTIN, LOW); // desliga o led do arduino
  pinMode(ma, OUTPUT);  //define pino de saida motor  A
  pinMode(mb, OUTPUT);  //define pino de saida motor  B
  pinMode(da, OUTPUT);  //define pino de saida motor  A
  pinMode(db, OUTPUT);  //define pino de saida motor  B
  pinMode(sa, INPUT);   //define pino de entrada sensor A
  pinMode(sb, INPUT);   //define pino de entrada sensor B
  delay(5000);          //Atraso para ligar os motores em mili segundos
  digitalWrite(da, LOW);//define pino como low assim dando partida no carrinho motor A
  digitalWrite(db, LOW);//define pino como low assim dando partida no carrinho motor B
  t = millis();         //variavel que demarca tempo atual
}
void loop() {
  if (millis >= 20000) {        //define o tempo que carrinho funcionara em mili segundos
    if ((millis() - t) > 200) {
      //define para que o sensor ultrasonico mande pulso a cada 200 mili segundos ou mais a partir do tempo decorrido da ligação do circuito sem ter que usar
      //delay que causa atraso no circuito e sem mandar pulsos toda hora causando bug por interferencia sonora de outros pulsos ja enviados
      d = ultrasonic.read();    //manda um pulso para o sensor ultrasonico medir a distancia e armazena em D
      t = millis();             //armazena o tempo atual em T
      // assim quando a diferença de tempo ultrapasar 200 mili pela diferença do tempo atual menos o tempo armazenado em T ele execulta esse comando e define t para o tempo atual
      //pois com t definido para igual tempo atual a difença que estava em mais de 200 mili segundos se torna 0 novamente.
    }
    if (d <= 20) {     // condição para o carrinho parar de acordo com a distancia estando menor ou igual a 20
      analogWrite(ma, 0); // desliga motor A
      analogWrite(mb, 0); // desliga motor B
      digitalWrite(LED_BUILTIN, HIGH);// liga o led do arduino
    } else if (int(digitalRead(sa)) == 0 && int(digitalRead(sb)) == 0) { // se não atender a condiçao de cima execulta essa assim se os dois sensores verem branco os dois motores ligam
      analogWrite(ma, v); // liga motor A
      analogWrite(mb, v); // liga motor A
      digitalWrite(LED_BUILTIN, LOW);// desliga o led do arduino
    } else if (int(digitalRead(sa)) == 1 && int(digitalRead(sb)) == 0) { // se não atender a condiçao de cima execulta essa assim se o sensor A ver preto ele desliga o motor A
      analogWrite(ma, 0); // desliga motor A
      analogWrite(mb, v); // liga motor B
      digitalWrite(LED_BUILTIN, LOW);// desliga o led do arduino
    } else if (int(digitalRead(sa)) == 0 && int(digitalRead(sb)) == 1) { // se não atender a condiçao de cima execulta essa assim se o sensor A ver preto ele desliga o motor B
      analogWrite(ma, v); // liga motor A
      analogWrite(mb, 0); // desliga motor B
      digitalWrite(LED_BUILTIN, LOW);// desliga o led do arduino
    }
  } else {
    analogWrite(ma, 0); // desliga motor A
    analogWrite(mb, 0); // desliga motor B
    digitalWrite(LED_BUILTIN, LOW);// desliga o led do arduino
  }
}
