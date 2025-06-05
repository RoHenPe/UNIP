//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// ctrl t auto formatação de texto
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#include <Ultrasonic.h>                                                        // biblioteca do sensor ultrasonico
#define ma 9                                                                   //Pino Velocidade 1º Motor ( 0 a 255)
#define mb 11                                                                  //Pino_Velocidade 2º Motor ( 0 a 255)
#define da 8                                                                   //Pino_Direção do 1º Motor (HIGH ou LOW)
#define db 10                                                                  //Pino_Direção do 2º Motor (HIGH ou LOW)
#define sa 6                                                                   //Pino_Sensor 1 
#define sb 5                                                                   //Pino_Sensor 2
#define pt 4                                                                   //Pino_Trigger
#define pe 3                                                                   //Pino_Echo
#define pl 12                                                                  //Pino_LED
int distancia;                                                                 //Variavel valor medido do sensor
int tempo = 100000000;                                                         //tempo que ele ficara ligado
int tempoLed = 500;                                                            //tempo de piscar o led led
int tempoSensor = 200;                                                         //Tempo que o circuito ficara ligado
int tempoInicio = 5000;                                                        //Tempo entre ligar e começar a rodar
int velocidade = 255;                                                          //velocidade dos motores Max 255,k,,,,,,,,,,,,,,,,,,,,,,
unsigned long t = millis();                                                    // tempo desde a ligação do arduino
unsigned long l = millis();                                                    // tempo desde a ligação do arduino
Ultrasonic ultrasonic(pt, pe);                                                 // inicia sensor ultrasonico
void setup() {                                                                 // seta todas as variaveis
  Serial.begin(9600);                                                          // inicia o serial para comunicar com computador
  pinMode(ma, OUTPUT);                                                         //define pino de saida motor  A
  pinMode(mb, OUTPUT);                                                         //define pino de saida motor  B
  pinMode(da, OUTPUT);                                                         //define pino de saida motor  A
  pinMode(db, OUTPUT);                                                         //define pino de saida motor  B
  pinMode(sa, INPUT);                                                          //define pino de entrada sensor A
  pinMode(sb, INPUT);                                                          //define pino de entrada sensor B
  pinMode(pl, OUTPUT);                                                         //define pino de entrada sensor B
  delay(tempoInicio);                                                          //Atraso para ligar os motores em mili segundos
  digitalWrite(da, LOW);                                                       //define pino como low assim dando partida no carrinho motor A
  digitalWrite(db, LOW);                                                       //define pino como low assim dando partida no carrinho motor B
  t = millis();                                                                //variavel que demarca tempo atual
  l = millis();                                                                //variavel que demarca tempo atual para o led
}
void loop() {                                                                  // inicia o loop
  int leituraA = digitalRead(sa);                                              //guarda valor lido em no sensor B
  int leituraB = digitalRead(sb);                                              //guarda valor lido em no sensor B
  if (millis() <= tempo)  {                                                    //define o tempo que carrinho funcionara em mili segundos mais o tempo que ele fica parado
    if ((millis() - t) > tempoSensor) {                                        //define para que o sensor ultrasonico mande pulso a cada 200 mili segundos ou mais a partir do tempo decorrido da ligação do circuito sem ter que usar
      //delay que causa atraso no circuito e sem mandar pulsos toda hora causando bug por interferencia sonora de outros pulsos ja enviados
      distancia = ultrasonic.read();                                           //manda um pulso para o sensor ultrasonico medir a distancia e armazena em D
      t = millis();                                                            //armazena o tempo atual em T
      // assim quando a diferença de tempo ultrapasar 200 mili pela diferença do tempo atual menos o tempo armazenado em T ele execulta esse comando e define t para o tempo atual
    }                                                                          //pois com t definido para igual tempo atual a difença que estava em mais de 200 mili segundos se torna 0 novamente.
    if (distancia <= 7 ) {                                                     // condição para o carrinho parar de acordo com a distancia estando menor ou igual a 20
      analogWrite(ma, 0);                                                      // desliga motor A
      analogWrite(mb, 0);                                                      // desliga motor B
      if ((millis() - l) > tempoLed) {                                         //tempo imposto para ligar
        digitalWrite(pl, HIGH);                                                // acende led
        l = millis();                                                          //armazena o tempo atual em l
      } else if ((millis() - l) > tempoLed / 2) {                              // tempo imposto para ligar led
        digitalWrite(pl, LOW);                                                 // desliga led
      }
    } else if (leituraA == 1 && leituraB == 1 or
               leituraA == 0 && leituraB == 0) {                               // se não atender a condiçao de cima execulta essa assim se os dois sensores verem branco os dois motores ligam
      analogWrite(ma, velocidade);                                             // liga motor A
      analogWrite(mb, velocidade);                                             // liga motor B
    } else if (leituraA == 0 && leituraB == 1) {                               // se não atender a condiçao de cima execulta essa assim se o sensor A ver preto ele desliga o motor A
      analogWrite(ma, 0);                                                      // desliga motor A
      analogWrite(mb, velocidade);                                             // liga motor B
    } else if (leituraA == 1 && leituraB == 0) {                               // se não atender a condiçao de cima execulta essa assim se o sensor A ver preto ele desliga o motor B
      analogWrite(ma, velocidade);                                             // liga motor A
      analogWrite(mb, 0);                                                      // desliga motor B
    }
  }
  else {
    analogWrite(ma, 0);                                                        // desliga motor A
    analogWrite(mb, 0);                                                        // desliga motor B
  }
  Serial.print("sa: "); Serial.println(leituraA);                              // retorna o valor medido para o computado
  Serial.print("sb: ");  Serial.println(leituraB);                             // retorna o valor medido para o computado
}
