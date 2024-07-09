import cv2
import serial
from ultralytics import YOLO
import serial.tools.list_ports

# Fungsi untuk menemukan port serial yang tersedia
def find_available_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        print(p)
        if "Arduino" in p.description:
            return p.device
    return None

# Mencari port yang tersedia
port = find_available_port()
if port is None:
    raise Exception("Port tidak tersedia. Pastikan port terhubung dan tidak digunakan oleh aplikasi lain.")

# Inisialisasi model YOLOv8
MODEL = 'MODEL_YOLO/best_yogya_8x.pt'
model = YOLO(MODEL)

# Membuka kamera (kamera default dengan indeks 0, sesuaikan jika menggunakan kamera lain)
cap = cv2.VideoCapture(0)

# Inisialisasi variabel untuk menghitung kendaraan
vehicle_count = 0
vehicle_ids = set()  # Untuk menyimpan ID unik kendaraan

# Penunjuk waktu
start_time = cv2.getTickCount()  # Waktu mulai
frequency = cv2.getTickFrequency()  # Frekuensi penunjuk waktu
interval = 0

# Inisialisasi serial untuk komunikasi dengan Arduino
ser = serial.Serial(port, 9600)

# Fungsi untuk mengklasifikasikan kepadatan lalu lintas dan menentukan durasi waktu lampu lalu lintas
def klasifikasikan_kepadatan(kepadatan):
    if 0 <= kepadatan <= 30:
        return "Sepi", 3  # Lalu lintas sepi, 3 detik
    elif 31 <= kepadatan <= 50:
        return "Normal", 5  # Lalu lintas normal, 5 detik
    elif 51 <= kepadatan <= 70:
        return "Ramai", 7  # Lalu lintas ramai, 7 detik
    elif 71 <= kepadatan <= 100:
        return "Padat", 10  # Lalu lintas padat, 10 detik
    else:
        return "Sangat Padat", 10  # Durasi maksimum untuk keamanan

# Fungsi untuk menghitung kepadatan berdasarkan jumlah kendaraan dan kapasitas area
def hitung_kepadatan(jumlah_kendaraan, kapasitas_area):
    return (jumlah_kendaraan / kapasitas_area) * 100

# Fungsi untuk menghitung durasi siklus terlama berdasarkan jumlah kendaraan dan rata-rata waktu
def hitung_durasi_siklus_terlama(jumlah_kendaraan, waktu_rata, jumlah_jalur):
    total_durasi = jumlah_kendaraan * waktu_rata
    return total_durasi / jumlah_jalur

# Fungsi untuk menghitung durasi lampu lalu lintas
def hitung_durasi_lampu(durasi_siklus_terlama, kepadatan):
    return durasi_siklus_terlama * (kepadatan / 100)

# Melakukan iterasi melalui frame kamera
while cap.isOpened():
    # Membaca satu frame dari kamera
    success, frame = cap.read()

    if success:
        # Menjalankan pelacakan YOLOv8 pada frame, mempertahankan pelacakan antar frame
        results = model.track(frame, persist=True, verbose=False)

        if results[0].boxes is not None:
            # Mendapatkan kotak dan ID pelacakan
            boxes = results[0].boxes.xywh.cpu()  # Koordinat kotak dalam format x, y, width, height
            if results[0].boxes.id is not None:
                track_ids = results[0].boxes.id.int().cpu().tolist()  # ID untuk setiap objek yang terdeteksi
            else:
                track_ids = [0] * len(boxes)  # Jika tidak ada ID, berikan nilai 0

            # Visualisasi hasil pada frame
            annotated_frame = results[0].plot()

            # Menambahkan ID unik ke set kendaraan
            for track_id in track_ids:
                vehicle_ids.add(track_id)

            # Menampilkan frame dengan anotasi
            cv2.imshow("Tracking", annotated_frame)
        else:
            # Jika tidak ada kotak terdeteksi
            print("No Vehicle detected in the current frame.")

        # Menghentikan loop jika tombol 'q' ditekan
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        # Menghitung waktu yang telah berlalu
        elapsed_time = (cv2.getTickCount() - start_time) / frequency

        # Jika interval waktu lampu lalu lintas telah berlalu, cetak total kendaraan dan reset waktu
        if elapsed_time >= interval:
            vehicle_count = len(boxes)  # Menghitung jumlah kendaraan unik
            
            # Reset penunjuk waktu dan ID kendaraan
            start_time = cv2.getTickCount()
            vehicle_ids.clear()
            
            # Parameter
            jumlah_kendaraan = vehicle_count  # Jumlah total kendaraan
            jumlah_jalur = 4  # Jumlah jalur
            kapasitas_area = 50  # Kapasitas maksimum area

            # Hitung kepadatan lalu lintas
            kepadatan = hitung_kepadatan(jumlah_kendaraan, kapasitas_area)
            print("Jumlah kendaraan terdeteksi:", jumlah_kendaraan)
            print(f"Kepadatan Lalu Lintas: {kepadatan:.2f}%")

            # Klasifikasikan kepadatan lalu lintas dan dapatkan waktu rata-rata
            klasifikasi, waktu_rata = klasifikasikan_kepadatan(kepadatan)

            # Hitung durasi siklus terlama
            durasi_siklus_terlama = hitung_durasi_siklus_terlama(jumlah_kendaraan, waktu_rata, jumlah_jalur)
            print(f"Durasi Siklus Terlama: {durasi_siklus_terlama:.2f} detik")

            # Cek jika jumlah kendaraan melebihi 50 atau kepadatan lebih dari 100%
            if jumlah_kendaraan > 50 or kepadatan > 100:
                durasi_lampu = 10  # Durasi maksimum
                print(f"Kondisi Lalu Lintas: Sangat Padat (jumlah kendaraan > 50 atau kepadatan > 100%)")
            else:
                # Hitung durasi lampu lalu lintas berdasarkan durasi siklus terlama dan kepadatan
                durasi_lampu = hitung_durasi_lampu(durasi_siklus_terlama, kepadatan)
                print(f"Kondisi Lalu Lintas: {klasifikasi}")
                print(f"Durasi Konstanta: {waktu_rata} detik")

            print(f"Durasi Lampu Lalu Lintas yang Dihitung (Durasi Lampu): {durasi_lampu:.2f} detik")
            
            # Perbarui interval berdasarkan durasi lampu
            interval = durasi_lampu + 4
            
            # Mengirim hanya durasi lampu ke Arduino melalui serial
            data = f"{durasi_lampu:.2f}\n"
            print(f"Mengirim data ke Arduino: {data.strip()}")  # Tambahkan print untuk debugging
            ser.write(data.encode())

    else:
        # Menghentikan loop jika akhir dari video tercapai
        break

# Melepaskan objek capture video dan menutup jendela tampilan
cap.release()
cv2.destroyAllWindows()
ser.close()
