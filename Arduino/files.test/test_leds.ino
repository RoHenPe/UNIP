const int ledVermelhoPin = 4;
const int ledAmareloPin = 8;
const int ledVerdePin = 7;

void setup() {
  pinMode(ledVermelhoPin, OUTPUT);
  pinMode(ledAmareloPin, OUTPUT);
  pinMode(ledVerdePin, OUTPUT);
}

void loop() {
  digitalWrite(ledVermelhoPin, HIGH);
  delay(500);
  digitalWrite(ledVermelhoPin, LOW);
  
  digitalWrite(ledAmareloPin, HIGH);
  delay(500);
  digitalWrite(ledAmareloPin, LOW);
  
  digitalWrite(ledVerdePin, HIGH);
  delay(500);
  digitalWrite(ledVerdePin, LOW);
  
  delay(1000);
}
