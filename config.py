# -*- coding: utf-8 -*-
"""
Cấu hình hệ thống IoT Lab 2 - B24DCVN086
Bao gồm thông số MQTT Broker, InfluxDB TSDB và các ngưỡng cảm biến.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Đường dẫn lưu trữ dữ liệu
RAW_CSV_PATH = os.path.join(DATA_DIR, "telemetry_raw.csv")
PROCESSED_CSV_PATH = os.path.join(DATA_DIR, "telemetry_preprocessed.csv")
METRICS_JSON_PATH = os.path.join(DATA_DIR, "system_metrics.json")

# Cấu hình MQTT Broker
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
MQTT_TOPIC = "lab2_B24DCVN086/esp32/telemetry"
MQTT_CLIENT_ID = "PYTHON-COLLECTOR-B24DCVN086"

# Cấu hình InfluxDB 2.x
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "iot_lab2_token_B24DCVN086_secret123")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "iot_lab")
INFLUXDB_BUCKET_RAW = os.getenv("INFLUXDB_BUCKET_RAW", "iot_raw")
INFLUXDB_BUCKET_PROCESSED = os.getenv("INFLUXDB_BUCKET_PROCESSED", "iot_processed")

# Chính sách lưu trữ (Retention Policy)
RETENTION_RAW_DAYS = 7
RETENTION_PROCESSED_DAYS = 30

# Tên Measurement trong InfluxDB
MEASUREMENT_RAW = "sensor_telemetry"
MEASUREMENT_PROCESSED = "sensor_preprocessed"

# Dải giá trị vật lý của cảm biến (dùng để validate)
SENSOR_BOUNDS = {
    "temperature": {"min": -40.0, "max": 80.0, "unit": "°C"},
    "humidity": {"min": 0.0, "max": 100.0, "unit": "%"},
    "distance_cm": {"min": 2.0, "max": 400.0, "unit": "cm"},
}

# Cấu hình phát hiện ngoại lai
OUTLIER_CONFIG = {
    "iqr_factor": 1.5,
    "zscore_threshold": 3.0,
}

# Cấu hình tái lấy mẫu (Resampling)
RESAMPLE_CONFIG = {
    "default_window": "30s",
    "aggregation_funcs": ["mean", "min", "max", "std"]
}

# Cấu hình trích xuất đặc trưng
FEATURE_CONFIG = {
    "rolling_window": 5,
}
