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
MODEL = 'MODEL_YOLO/best_yogya_8x_80_10_10.pt'
model = YOLO(MODEL)

# Membuka file video
video_path = "DATA_UJI/normal 2.jpg"
cap = cv2.VideoCapture(video_path)

# Inisialisasi variabel untuk menghitung kendaraan
vehicle_count = 0

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

# Melakukan iterasi melalui frame kamera
while cap.isOpened():
    # Membaca satu frame dari kamera
    success, frame = cap.read()

    if success:
        # Menghitung waktu yang telah berlalu
        elapsed_time = (cv2.getTickCount() - start_time) / frequency

        # Tentukan apakah akan menggunakan verbose
        verbose = elapsed_time >= interval

        # Menjalankan pelacakan YOLOv8 pada frame, dengan verbose sesuai kondisi
        results = model.track(frame, persist=True, verbose=verbose)

        if results[0].boxes is not None:
            # Mendapatkan kotak dan ID pelacakan
            boxes = results[0].boxes.xywh.cpu()  # Koordinat kotak dalam format x, y, width, height

            # Visualisasi hasil pada frame
            annotated_frame = results[0].plot(line_width=1, font_size=6)

            # Menghitung jumlah kendaraan yang terdeteksi
            vehicle_count = len(boxes)

            # Menampilkan frame dengan anotasi
            cv2.imshow("Tracking", annotated_frame)
        else:
            # Jika tidak ada kotak terdeteksi
            print("No Vehicle detected in the current frame.")
            vehicle_count = 0

        # Menghentikan loop jika tombol 'q' ditekan
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        # Menghitung waktu yang telah berlalu
        elapsed_time = (cv2.getTickCount() - start_time) / frequency

        # Jika interval waktu lampu lalu lintas telah berlalu, cetak total kendaraan dan reset waktu
        if verbose:
            # Reset penunjuk waktu
            start_time = cv2.getTickCount()

            # Parameter
            jumlah_kendaraan = vehicle_count  # Jumlah total kendaraan
            jumlah_jalur = 4  # Jumlah jalur
            kapasitas_area = 50  # Kapasitas maksimum area

            # Hitung kepadatan lalu lintas
            kepadatan = hitung_kepadatan(jumlah_kendaraan, kapasitas_area)
            print(f"Jumlah kendaraan terdeteksi: {jumlah_kendaraan}")
            print(f"Kepadatan Lalu Lintas: {kepadatan:.2f}%")

            # Klasifikasikan kepadatan lalu lintas dan dapatkan waktu rata-rata
            klasifikasi, waktu_rata = klasifikasikan_kepadatan(kepadatan)

            # Hitung durasi siklus terlama
            durasi_siklus_terlama = hitung_durasi_siklus_terlama(jumlah_kendaraan, waktu_rata, jumlah_jalur)

            # Cek jika jumlah kendaraan melebihi 50 atau kepadatan lebih dari 100%
            if kepadatan > 100:
                durasi_lampu = 180
                print("Kondisi Lalu Lintas: Sangat Padat (jumlah kepadatan > 100%)")
            else:
                # Gunakan durasi siklus terlama langsung untuk durasi lampu lalu lintas
                durasi_lampu = round(min(max(durasi_siklus_terlama, 5), 180))
                print(f"Kondisi Lalu Lintas: {klasifikasi}")
                print(f"Durasi Konstanta: {waktu_rata} detik")
            
            print(f"Durasi Lampu Lalu Lintas yang Dihitung: {durasi_siklus_terlama:.2f} detik")
            print(f"Durasi Lampu Lalu Lintas yang Diterapkan: {durasi_lampu} detik")
            
            # Durasi lampu tunggu tetap 4 detik
            durasi_tunggu = 4

            # Perbarui interval berdasarkan durasi lampu
            interval = durasi_lampu + durasi_tunggu
            
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
