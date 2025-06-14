#include <Adafruit_APDS9960.h>
#include <Wire.h>

Adafruit_APDS9960 apds;

void setup() {
  Serial.begin(115200);
  
  if(!apds.begin()) {
    Serial.println("Falha ao inicializar APDS9960!");
    while(1);
  }
  
  apds.enableColor(true);
  apds.enableGesture(true);
  Serial.println("Sensor APDS9960 pronto!");
}

void loop() {
  // Detecção de gestos
  if(apds.gestureValid()) {
    int gesture = apds.readGesture();
    switch(gesture) {
      case APDS9960_UP:     Serial.println("Gesto: CIMA"); break;
      case APDS9960_DOWN:   Serial.println("Gesto: BAIXO"); break;
      case APDS9960_LEFT:   Serial.println("Gesto: ESQUERDA"); break;
      case APDS9960_RIGHT:  Serial.println("Gesto: DIREITA"); break;
    }
  }

  // Leitura de cor
  if(apds.colorDataReady()) {
    uint16_t r, g, b, c;
    apds.getColorData(&r, &g, &b, &c);
    Serial.print("Cor R:"); Serial.print(r);
    Serial.print(" G:"); Serial.print(g);
    Serial.print(" B:"); Serial.print(b);
    Serial.print(" C:"); Serial.println(c);
  }
  
  delay(100);
}
