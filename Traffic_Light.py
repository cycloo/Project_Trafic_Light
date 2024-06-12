import cv2
import numpy as np
from collections import defaultdict
from ultralytics import YOLO

# Inisialisasi model YOLOv8
MODEL = 'best_yogya_8x.pt'
model = YOLO(MODEL)

# Membuka file video
video_path = "testing.mp4"
cap = cv2.VideoCapture(video_path)

# Menyimpan riwayat pelacakan
track_history = defaultdict(lambda: [])

# Inisialisasi variabel untuk menghitung kendaraan
vehicle_count = 0
vehicle_ids = set()  # Untuk menyimpan ID unik kendaraan

# Penunjuk waktu
start_time = cv2.getTickCount() # Waktu mulai
frequency = cv2.getTickFrequency() # Frekuensi penunjuk waktu
interval = 10 # 60 detik

# Melakukan iterasi melalui frame video
while cap.isOpened():
    # Membaca satu frame dari video
    success, frame = cap.read()

    if success:
        # Menjalankan pelacakan YOLOv8 pada frame, mempertahankan pelacakan antar frame
        results = model.track(frame, persist=True, verbose=False)

        # Mendapatkan kotak dan ID pelacakan
        boxes = results[0].boxes.xywh.cpu()  # Koordinat kotak dalam format x, y, width, height
        track_ids = results[0].boxes.id.int().cpu().tolist()  # ID untuk setiap objek yang terdeteksi

        # Visualisasi hasil pada frame
        annotated_frame = results[0].plot()

        # Menggambar lintasan
        for box, track_id in zip(boxes, track_ids):
            x, y, w, h = box
            track = track_history[track_id]
            track.append((float(x), float(y)))  # Menambahkan titik pusat x, y ke riwayat pelacakan
            if len(track) > 30:  # hanya 30 lintasan terakhir untuk setiap objek
                track.pop(0)

            # Menggambar garis pelacakan
            points = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated_frame, [points], isClosed=False, color=(130, 130, 130), thickness=2)

            # Menambahkan ID unik ke set kendaraan
            vehicle_ids.add(track_id)

        # Menampilkan frame dengan anotasi
        cv2.imshow("Tracking", annotated_frame)

        # Menghentikan loop jika tombol 'q' ditekan
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        # Menghitung waktu yang telah berlalu
        elapsed_time = (cv2.getTickCount() - start_time) / frequency

        # Jika interval 60 detik telah berlalu, cetak total kendaraan dan reset waktu
        if elapsed_time >= interval:
            vehicle_count = len(vehicle_ids)  # Menghitung jumlah kendaraan unik
            print("Total number of vehicles detected in the last 60 seconds:", vehicle_count)
            # Reset penunjuk waktu dan ID kendaraan
            start_time = cv2.getTickCount()
            vehicle_ids.clear()
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

            # Hitung durasi lampu lalu lintas berdasarkan durasi siklus terlama dan kepadatan
            durasi_lampu = hitung_durasi_lampu(durasi_siklus_terlama, kepadatan)
            print(f"Kondisi Lalu Lintas: {klasifikasi}")
            print(f"Durasi Konstanta: {waktu_rata} detik")
            print(f"Durasi Lampu Lalu Lintas yang Dihitung (Durasi Lampu): {durasi_lampu:.2f} detik")

    else:
        # Menghentikan loop jika akhir dari video tercapai
        break

# Melepaskan objek capture video dan menutup jendela tampilan
cap.release()
cv2.destroyAllWindows()

