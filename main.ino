#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// Set the LCD address to 0x27 for a 16 chars and 2 line display
LiquidCrystal_I2C lcd(0x27, 16, 2);

// --- Define Buzzer Pin (MUST use a PWM pin, like 9, for volume control) ---
const int BUZZER_PIN = 9; 

void setup() {
  Serial.begin(9600);
  
  // Initialize the LCD
  lcd.init();
  lcd.backlight();
  
  // Set buzzer pin mode
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Print initial message
  lcd.setCursor(0, 0);
  lcd.print("Server Ready!");
}

void loop() {
  if (Serial.available() > 0) {
    // Read the string until newline character '\n'
    String receivedText = Serial.readStringUntil('\n');
    int separatorIndex = receivedText.indexOf('|');
    
    lcd.clear(); // Clear old display
    
    if (separatorIndex != -1) {
      String line1 = receivedText.substring(0, separatorIndex); 
      String line2 = receivedText.substring(separatorIndex + 1); 
      
      lcd.setCursor(0, 0);
      lcd.print(line1);
      
      lcd.setCursor(0, 1);
      lcd.print(line2);
    } else {
      // Fallback if no '|' is found
      lcd.setCursor(0, 0);
      lcd.print(receivedText);
    }
    
    // Call the function to trigger the buzzer
    beepTwice();
  }
}

// --- Function to make the buzzer beep twice at low volume ---
void beepTwice() {
  for (int i = 0; i < 2; i++) {
    // analogWrite(pin, value). Value is 0 to 255. 
    // 5 is very quiet. Change to 10 or 20 if it's too quiet.
    analogWrite(BUZZER_PIN, 10); 
    delay(100);                     
    
    // Turn off buzzer
    analogWrite(BUZZER_PIN, 0);  
    delay(100);                     
  }
}
