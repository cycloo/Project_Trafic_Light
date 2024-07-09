// Definisikan pin untuk setiap segmen pada ketiga display
const int segmentPins[3][7] = {    
  {22, 23, 24, 25, 26, 27, 28}, // Display 1  
  {38, 39, 40, 41, 42, 43, 44}, // Display 2
  {46, 47, 48, 49, 50, 51, 52} // Display 3
};

// Definisikan tampilan angka 0-9 pada display 7 segment common anode menggunakan byte
const byte numbers[10] = {
  0b00111111, // 0
  0b00000110, // 1
  0b01011011, // 2
  0b01001111, // 3
  0b01100110, // 4
  0b01101101, // 5
  0b01111101, // 6
  0b00000111, // 7
  0b01111111, // 8
  0b01101111  // 9
};

// Pin yang terhubung ke lampu lalu lintas
const int redPins[4] = {4, 5, 8, 13};
const int yellowPins[4] = {3, 6, 9, 12};
const int greenPins[4] = {2, 7, 10, 11};

String receivedData = "";
bool dataAvailable = false;
int currentLane = 0;

// Fungsi untuk menampilkan angka pada display
void displayNumber(int display, int num) {
  byte segments = numbers[num];
  for (int i = 0; i < 7; i++) {
    digitalWrite(segmentPins[display][i], !(segments & (1 << i)));
  }
}

void setup() {
  // Atur semua pin segmen sebagai output
  for (int display = 0; display < 3; display++) {
    for (int i = 0; i < 7; i++) {
      pinMode(segmentPins[display][i], OUTPUT);
    }
  }

  // Inisialisasi pin lampu lalu lintas sebagai output
  for (int i = 0; i < 4; i++) {
    pinMode(redPins[i], OUTPUT);
    pinMode(yellowPins[i], OUTPUT);
    pinMode(greenPins[i], OUTPUT);
    digitalWrite(redPins[i], HIGH); // Set semua lampu merah ke HIGH pada awalnya
    digitalWrite(yellowPins[i], LOW);
    digitalWrite(greenPins[i], LOW);
  }

  // Inisialisasi komunikasi serial
  Serial.begin(9600);
  Serial.println("Arduino ready");
}

void loop() {
  // Memeriksa apakah ada data yang tersedia di serial
  if (Serial.available() > 0) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      dataAvailable = true;
    } else {
      receivedData += inChar;
    }
  }

  if (dataAvailable) {
    Serial.println("Data diterima: " + receivedData);

    // Mengubah durasi dari string ke float
    float duration = receivedData.toFloat();
    Serial.println("Durasi diterima: " + String(duration) + " detik");

    // Mengatur lampu lalu lintas berdasarkan durasi yang diterima
    for (int i = 0; i < 4; i++) {
      if (i == currentLane) {
        if (duration == 0) {
          // Langsung pindah jalur jika durasi adalah 0
          continue;
        }

        // Merah ke hijau
        digitalWrite(redPins[i], LOW);
        digitalWrite(greenPins[i], HIGH);

        for (int j = (int)duration; j >= 0; j--) {
          int hundreds = j / 100;
          int tens = (j / 10) % 10;
          int units = j % 10;

          displayNumber(0, hundreds);
          displayNumber(1, tens);
          displayNumber(2, units);

          delay(1000); // Tunggu 1 detik sebelum menampilkan angka berikutnya
        }

        digitalWrite(greenPins[i], LOW);
        digitalWrite(yellowPins[i], HIGH);
        delay(2000); // Durasi lampu kuning tetap 2 detik

        digitalWrite(yellowPins[i], LOW);
        digitalWrite(redPins[i], HIGH);

      } else {
        // Tetap merah untuk jalur lainnya
        digitalWrite(redPins[i], HIGH);
        digitalWrite(greenPins[i], LOW);
        digitalWrite(yellowPins[i], LOW);
      }
    }

    // Pindah ke jalur berikutnya
    currentLane = (currentLane + 1) % 4;

    // Reset data yang diterima
    receivedData = "";
    dataAvailable = false;
  }
}