#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
  Serial.begin(9600);
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Teste LCD OK!");
  lcd.setCursor(0, 1);
  lcd.print("Linha 2 Funciona");
}

void loop() {
  // Teste cíclico do display
  static unsigned long lastChange = millis();
  static bool state = false;
  
  if(millis() - lastChange > 1000) {
    state = !state;
    lcd.setCursor(14, 1);
    lcd.print(state ? "*" : " ");
    lastChange = millis();
  }
}
