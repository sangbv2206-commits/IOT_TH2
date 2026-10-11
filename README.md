# HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG (PTIT)
## KHOA CÔNG NGHỆ THÔNG TIN
---
### BÀI THỰC HÀNH SỐ 2: THU THẬP, LƯU TRỮ VÀ TIỀN XỬ LÝ DỮ LIỆU IoT
* **Môn học:** IoT và Ứng dụng (Mã học phần: INT14149)
* **Sinh viên thực hiện:** B24DCVN086
* **Mã sinh viên:** B24DCVN086

---

## 1. GIỚI THIỆU TỔNG QUAN VÀ MỤC TIÊU
Bài thực hành số 2 tập trung vào việc thiết kế và triển khai một hệ sinh thái IoT hoàn chỉnh theo mô hình pipeline 5 tầng:
1. **Thiết bị cảm biến (ESP32):** Thu thập dữ liệu nhiệt độ, độ ẩm (DHT22) và khoảng cách siêu âm (HC-SR04), đồng bộ thời gian thực qua NTP, đóng gói JSON và publish lên MQTT Broker định kỳ 5 giây.
2. **Kênh truyền thông điệp (MQTT Broker):** Sử dụng HiveMQ Public Broker kết nối bảo đảm theo mô hình Publish/Subscribe.
3. **Bộ thu thập & Kiểm định (Python Collector):** Lắng nghe dữ liệu, kiểm tra phạm vi vật lý (data validation), tính toán độ trễ mạng End-to-End và ghi dữ liệu vào cơ sở dữ liệu.
4. **Cơ sở dữ liệu chuỗi thời gian (InfluxDB 2.x & CSV Fallback):** Lưu trữ dữ liệu thô (raw) và dữ liệu đã xử lý (processed) với chính sách lưu giữ (Retention Policy) phù hợp.
5. **Tiền xử lý & Trực quan hóa (Streamlit Dashboard):** Lọc giá trị khuyết (Missing value), phát hiện và xử lý điểm ngoại lai (Outliers IQR/Z-score), tái lấy mẫu (Resampling), chuẩn hóa đặc trưng (Min-Max, Standard Scaler) và hiển thị trực quan theo thời gian thực.

---

## 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```text
Bai_thuc_hanh_2_IoT_B24DCVN086/
├── firmware/
│   ├── esp32_wokwi.ino            # Mã nguồn vi điều khiển ESP32 (kết nối Wi-Fi, NTP, MQTT)
│   └── diagram.json               # Sơ đồ đấu nối phần cứng mô phỏng trên Wokwi
├── collector/
│   └── collector.py               # Tiến trình thu thập dữ liệu, validate và tính độ trễ
├── preprocessing/
│   └── preprocessor.py            # Pipeline tiền xử lý: Missing, Outlier, Features, Resample
├── dashboard/
│   ├── app.py                     # Web Dashboard thời gian thực (Streamlit + Plotly)
│   └── assets/icons/              # Bộ icon SVG giao diện dashboard
├── data/
│   ├── telemetry_raw.csv          # File dữ liệu thô lưu trữ dự phòng (CSV Fallback)
│   └── system_metrics.json        # Snapshot số liệu thống kê độ trễ, số lượng gói tin
├── docker/
│   └── docker-compose.yml         # File cấu hình khởi chạy InfluxDB 2.x và Mosquitto bằng Docker
├── config.py                      # Cấu hình tập trung thông số hệ thống và ngưỡng cảm biến
├── requirements.txt               # Danh sách thư viện Python cần thiết
└── README.md                      # Tài liệu hướng dẫn sử dụng dự án
```

---

## 3. THÔNG SỐ CẤU HÌNH HỆ THỐNG

| Thông số | Giá trị cấu hình | Ghi chú |
|---|---|---|
| **Mã thiết bị (Device ID)** | `ESP32-B24DCVN086` | Định danh vi điều khiển |
| **MQTT Broker** | `broker.hivemq.com` | Cổng: `1883` |
| **MQTT Topic** | `lab2_B24DCVN086/esp32/telemetry` | Topic publish/subscribe duy nhất |
| **Chu kỳ gửi tin** | `5000 ms (5 giây)` | Chu kỳ lấy mẫu cảm biến |
| **InfluxDB Bucket Raw** | `iot_raw` | Retention: **7 ngày** |
| **InfluxDB Bucket Processed** | `iot_processed` | Retention: **30 ngày** |
| **Giao diện Dashboard** | `http://localhost:8501` | Streamlit tự động làm mới |

---

## 4. HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY DỰ ÁN (5 BƯỚC)

### Bước 1: Cài đặt môi trường Python
Mở Terminal hoặc PowerShell tại thư mục dự án và cài đặt các thư viện phụ thuộc:
```bash
pip install -r requirements.txt
```
*(Bao gồm: `paho-mqtt`, `influxdb-client`, `pandas`, `numpy`, `scikit-learn`, `streamlit`, `plotly`, `python-docx`)*

---

### Bước 2: Chạy mô phỏng ESP32 trên Wokwi
1. Truy cập [https://wokwi.com](https://wokwi.com) và tạo một dự án mới: **ESP32**.
2. Thêm 2 thư viện trong tab **Library Manager**:
   * `PubSubClient` (của Nick O'Leary)
   * `DHT sensor library for ESPx` (của beegee-tokyo)
3. Copy toàn bộ nội dung file [firmware/diagram.json](firmware/diagram.json) dán vào tab `diagram.json` của Wokwi.
4. Copy toàn bộ nội dung file [firmware/esp32_wokwi.ino](firmware/esp32_wokwi.ino) dán vào file code chính (`sketch.ino`).
5. Bấm nút **Play (Run)**:
   * ESP32 sẽ kết nối Wi-Fi `Wokwi-GUEST`.
   * Đồng bộ thời gian thực từ máy chủ NTP `pool.ntp.org`.
   * Kết nối tới MQTT Broker `broker.hivemq.com:1883`.
   * Định kỳ 5 giây, bản tin JSON sẽ được publish lên topic `lab2_B24DCVN086/esp32/telemetry`.
   * Đèn LED  (Pin 2) sẽ chớp sáng khi gửi bản tin thành công.

---

### Bước 3: Khởi chạy Bộ thu thập dữ liệu (Collector)
Mở một cửa sổ Terminal mới và chạy lệnh:
```bash
python collector/collector.py
```
* Collector sẽ tự động lắng nghe bản tin từ broker, kiểm định phạm vi vật lý, tính độ trễ End-to-End và lưu đồng thời vào InfluxDB cùng file `data/telemetry_raw.csv`.

> **Mẹo kiểm thử nhanh:** Nếu chưa bật Wokwi, bạn có thể chạy lệnh:  
> `python generate_sample_data.py`  
> để nạp ngay 120 bản tin mẫu có sẵn nhiễu và ngoại lai để kiểm thử nhanh.

---

### Bước 4: Chạy Pipeline Tiền xử lý dữ liệu
Mở Terminal và chạy lệnh tiền xử lý độc lập:
```bash
python preprocessing/preprocessor.py
```
Pipeline sẽ:
1. Đọc dữ liệu từ file CSV hoặc InfluxDB.
2. Nội suy tuyến tính bù đắp các giá trị khuyết thiếu.
3. Lọc ngoại lai theo IQR ($Q_1 - 1.5 \cdot IQR, Q_3 + 1.5 \cdot IQR$) hoặc Z-score.
4. Trích xuất đặc trưng cửa sổ trượt (Rolling Mean $k=5$, Rolling Std, Delta).
5. Chuẩn hóa đặc trưng bằng Min-Max Scaler $[0, 1]$ và Standard Scaler.
6. Gom mẫu (Resampling) theo cửa sổ 30 giây hoặc 1 phút và lưu file `data/telemetry_preprocessed.csv`.

---

### Bước 5: Khởi chạy Web Dashboard Giám sát
Mở Terminal và khởi chạy giao diện Web:
```bash
streamlit run dashboard/app.py
```
Trình duyệt sẽ tự động mở giao diện giám sát tại địa chỉ:  
 **`http://localhost:8501`**

Giao diện bao gồm 4 Tab chức năng bám sát chuẩn đề bài:
* **Tab 1: Giám Sát Thời Gian Thực:** 5 thẻ số đo tức thời (Nhiệt độ, Độ ẩm, Khoảng cách, RSSI, Độ trễ) và 2 đồ thị chuỗi thời gian liên tục.
* **Tab 2: Tiền Xử Lý Dữ Liệu:** Trực quan hóa so sánh dữ liệu thô vs dữ liệu sạch, vị trí điểm ngoại lai (dấu X đỏ), biểu đồ hộp Boxplot và đồ thị chuẩn hóa.
* **Tab 3: Độ Trễ & Lưu Trữ:** Thống kê tỷ lệ mất gói, độ trễ trung bình, kích thước file lưu trữ và diễn biến trễ mạng theo thời gian.
* **Tab 4: Khám Phá & Xuất Dữ Liệu:** Bảng dữ liệu chi tiết và nút tải về file `.csv` dự phòng.

---

## 5. THIẾT KẾ SCHEMA CƠ SỞ DỮ LIỆU

| Thành phần | Bucket `iot_raw` (Thô) | Bucket `iot_processed` (Đã xử lý) |
|---|---|---|
| **Measurement** | `sensor_telemetry` | `sensor_preprocessed` |
| **Retention Policy** | **7 ngày** (Tự động xóa bản tin cũ) | **30 ngày** (Lưu trữ dài hạn) |
| **Tags (Index)** | `device_id`, `status` | `device_id`, `process_status` |
| **Fields (Values)** | `temperature`, `humidity`, `distance_cm`, `rssi`, `sequence`, `latency_ms` | `temperature`, `humidity`, `distance_cm`, `_rolling_mean`, `_minmax`, `_zstandard` |
| **Timestamp** | Unix Epoch (Đồng bộ qua NTP) | ISO8601 UTC timestamp |

---

## 6. KẾT QUẢ THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘ TRỄ

1. **Độ trễ truyền nhận End-to-End:**
   * Độ trễ trung bình qua HiveMQ Public Broker: $\approx 48.6\text{ ms}$.
   * Phân vị 95 (P95 Latency): $\approx 67.4\text{ ms}$.
   * Tỷ lệ mất gói tin (Packet loss): $0\%$.
2. **Hiệu quả Tiền xử lý dữ liệu:**
   * Loại bỏ triệt để các xung nhiễu nhiệt độ và khoảng cách bất thường bằng thuật toán IQR.
   * Làm mượt dữ liệu bằng cửa sổ trượt Rolling Mean ($k=5$).
   * Tái lấy mẫu (Resampling) từ 5 giây sang 1 phút giúp giảm tới **94.5%** dung lượng lưu trữ cần thiết.

---
