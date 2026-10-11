# -*- coding: utf-8 -*-
import os
import sys
import json
import random
import time
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
import config
from preprocessing.preprocessor import IoTDataPreprocessor

ICONS_DIR = os.path.join(os.path.dirname(__file__), "assets", "icons")

def get_svg_icon(name, size=18):
    path = os.path.join(ICONS_DIR, f"{name}.svg")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            svg = f.read().strip()
        return f'<span style="display:inline-flex;vertical-align:middle;width:{size}px;height:{size}px;margin-right:6px;">{svg}</span>'
    return ""

st.set_page_config(
    page_title="Hệ Thống Thu Thập & Tiền Xử Lý Dữ Liệu IoT",
    page_icon="assets/icons/chip.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title { font-size: 24px; font-weight: 700; color: #0F172A; margin-bottom: 2px; }
    .sub-title  { font-size: 13px; color: #64748B; margin-bottom: 20px; }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px 16px;
        text-align: left;
    }
    .metric-label { font-size: 12px; color: #64748B; font-weight: 600; margin-bottom: 6px; }
    .metric-value { font-size: 26px; font-weight: 700; color: #0F172A; }
    .metric-sub   { font-size: 11px; color: #94A3B8; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_preprocessor():
    return IoTDataPreprocessor()

preprocessor = get_preprocessor()

def load_data():
    return preprocessor.load_raw_data()

# ================= SIDEBAR =================
st.sidebar.markdown(f"### {get_svg_icon('settings', 20)} Cấu Hình Hệ Thống", unsafe_allow_html=True)
st.sidebar.markdown("**Mã sinh viên:** B24DCVN086")
st.sidebar.markdown("**Môn học:** IoT và Ứng dụng (INT14149)")
st.sidebar.markdown(f"**MQTT Broker:** `{config.MQTT_BROKER}`")
st.sidebar.markdown(f"**MQTT Topic:** `{config.MQTT_TOPIC}`")

st.sidebar.markdown("---")
st.sidebar.markdown(f"### {get_svg_icon('chart', 20)} Tham Số Tiền Xử Lý", unsafe_allow_html=True)
outlier_method  = st.sidebar.radio("Phát hiện ngoại lai:", ["IQR", "Z-score"], index=0)
outlier_action  = st.sidebar.selectbox("Xử lý ngoại lai:", ["Cắt biên (Winsorizing)", "Nội suy (Interpolate)"], index=0)
resample_window = st.sidebar.selectbox("Cửa sổ gom mẫu:", ["15s", "30s", "1min", "5min"], index=1)
rolling_window  = st.sidebar.slider("Cửa sổ trượt (Rolling):", min_value=3, max_value=15, value=5, step=1)

col_act1, col_act2 = st.sidebar.columns(2)
with col_act1:
    if st.button("Làm mới"):
        st.rerun()
with col_act2:
    if st.button("Tạo mẫu thử"):
        from generate_sample_data import generate_sample_dataset
        generate_sample_dataset(num_points=120)
        st.success("Đã sinh 120 mẫu dữ liệu!")
        st.rerun()

auto_refresh = st.sidebar.checkbox("Tự động làm mới (5s)", value=True)
if auto_refresh:
    st_autorefresh(interval=5000, key="iot_telemetry_autorefresh")

# ================= HEADER =================
st.markdown('<div class="main-title">HỆ THỐNG THU THẬP, LƯU TRỮ VÀ TIỀN XỬ LÝ DỮ LIỆU IoT</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Pipeline: ESP32 (DHT22, HC-SR04) &#8594; HiveMQ MQTT &#8594; Python Collector &#8594; InfluxDB TSDB &#8594; Tiền xử lý &#8594; Web Dashboard</div>', unsafe_allow_html=True)

df_raw = load_data()

if df_raw.empty:
    st.warning("Chưa nhận được dữ liệu cảm biến. Hãy bật mô phỏng ESP32 trên Wokwi hoặc bấm nút 'Tạo mẫu thử' ở thanh bên trái.")
    st.stop()

df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=True)
latest_row = df_raw.iloc[-1]

tab1, tab2, tab3, tab4 = st.tabs([
    "Giám Sát Thời Gian Thực",
    "Tiền Xử Lý Dữ Liệu",
    "Độ Trễ & Lưu Trữ",
    "Khám Phá & Xuất Dữ Liệu"
])

# ================= TAB 1 =================
with tab1:
    st.markdown("##### Số Đo Cảm Biến Thời Gian Thực")
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        val_t = f"{latest_row['temperature']:.1f} °C" if pd.notna(latest_row['temperature']) else "N/A"
        st.markdown(f'<div class="metric-card"><div class="metric-label">{get_svg_icon("temp",16)} Nhiệt Độ DHT22</div><div class="metric-value">{val_t}</div><div class="metric-sub">Phạm vi: -40..80 °C</div></div>', unsafe_allow_html=True)

    with m2:
        val_h = f"{latest_row['humidity']:.1f} %" if pd.notna(latest_row['humidity']) else "N/A"
        st.markdown(f'<div class="metric-card"><div class="metric-label">{get_svg_icon("humidity",16)} Độ Ẩm DHT22</div><div class="metric-value">{val_h}</div><div class="metric-sub">Phạm vi: 0..100 %</div></div>', unsafe_allow_html=True)

    with m3:
        val_d = f"{latest_row['distance_cm']:.1f} cm" if pd.notna(latest_row['distance_cm']) else "N/A"
        st.markdown(f'<div class="metric-card"><div class="metric-label">{get_svg_icon("distance",16)} Khoảng Cách HC-SR04</div><div class="metric-value">{val_d}</div><div class="metric-sub">Phạm vi: 2..400 cm</div></div>', unsafe_allow_html=True)

    with m4:
        val_r = f"{latest_row['rssi']:.0f} dBm" if pd.notna(latest_row['rssi']) else "N/A"
        st.markdown(f'<div class="metric-card"><div class="metric-label">{get_svg_icon("wifi",16)} Sóng Wi-Fi (RSSI)</div><div class="metric-value">{val_r}</div><div class="metric-sub">Tốt: &gt; -70 dBm</div></div>', unsafe_allow_html=True)

    with m5:
        val_l = f"{latest_row['latency_ms']:.1f} ms" if "latency_ms" in latest_row.index and pd.notna(latest_row['latency_ms']) else "N/A"
        st.markdown(f'<div class="metric-card"><div class="metric-label">{get_svg_icon("speed",16)} Độ Trễ End-to-End</div><div class="metric-value">{val_l}</div><div class="metric-sub">Broker: HiveMQ</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### Nhiệt Độ & Độ Ẩm Theo Thời Gian")
        fig_th = go.Figure()
        fig_th.add_trace(go.Scatter(
            x=df_raw["timestamp"], y=df_raw["temperature"],
            mode="lines+markers" if len(df_raw) < 25 else "lines",
            name="Nhiệt độ (°C)", line=dict(color="#FF4B4B", width=2)
        ))
        fig_th.add_trace(go.Scatter(
            x=df_raw["timestamp"], y=df_raw["humidity"],
            mode="lines+markers" if len(df_raw) < 25 else "lines",
            name="Độ ẩm (%)", line=dict(color="#0068C9", width=2), yaxis="y2"
        ))
        fig_th.update_layout(
            xaxis=dict(title="Thời gian"),
            yaxis=dict(title=dict(text="Nhiệt độ (°C)", font=dict(color="#FF4B4B"))),
            yaxis2=dict(title=dict(text="Độ ẩm (%)", font=dict(color="#0068C9")), overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=370, margin=dict(l=40, r=40, t=50, b=40)
        )
        st.plotly_chart(fig_th, use_container_width=True)

    with c2:
        st.markdown("##### Khoảng Cách HC-SR04 Theo Thời Gian")
        fig_d = px.line(
            df_raw, x="timestamp", y="distance_cm", color_discrete_sequence=["#00B4D8"],
            markers=len(df_raw) < 25
        )
        max_dist = df_raw["distance_cm"].max() if not df_raw["distance_cm"].isna().all() else 400
        fig_d.add_hline(
            y=min(max_dist * 0.9, 380), line_dash="dot", line_color="#EF4444",
            annotation_text="Ngưỡng cảnh báo (~90%)"
        )
        fig_d.update_layout(xaxis=dict(title="Thời gian"), yaxis=dict(title="Khoảng cách (cm)"),
                            height=370, margin=dict(l=40, r=40, t=50, b=40))
        st.plotly_chart(fig_d, use_container_width=True)

# ================= TAB 2 =================
with tab2:
    st.markdown("##### Pipeline Tiền Xử Lý Dữ Liệu (Xử Lý Khuyết Thiếu, Ngoại Lai, Gom Mẫu & Chuẩn Hóa)")

    method_key = "iqr" if outlier_method == "IQR" else "zscore"
    action_type = "clip" if "Cắt biên" in outlier_action or "clip" in outlier_action else "interpolate"

    try:
        df_step1, missing_report = preprocessor.handle_missing_values(df_raw, method="interpolate")
        df_step2, outlier_report = preprocessor.handle_outliers(df_step1, method=method_key, action=action_type)
        df_step3 = preprocessor.engineer_features(df_step2, window=rolling_window)
        df_final = preprocessor.normalize_features(df_step3)
        df_res = preprocessor.resample_data(df_final, time_window=resample_window)
        df_proc = df_final
    except Exception as e:
        st.error(f"Lỗi tiền xử lý dữ liệu: {e}")
        df_proc = pd.DataFrame()
        df_res = pd.DataFrame()
        missing_report = {}
        outlier_report = {}

    if not df_proc.empty:
        st_c1, st_c2, st_c3, st_c4 = st.columns(4)
        with st_c1:
            st.metric("Tổng Số Bản Tin Thô", len(df_raw))
        with st_c2:
            missing_total = sum(missing_report.values()) if missing_report else 0
            st.metric("Giá Trị Khuyết Đã Nội Suy", missing_total)
        with st_c3:
            outlier_total = sum(v["count"] for v in outlier_report.values()) if outlier_report else 0
            st.metric(f"Ngoại Lai Phát Hiện ({outlier_method})", outlier_total)
        with st_c4:
            st.metric("Số Điểm Sau Gom Mẫu", len(df_res) if not df_res.empty else 0)

        st.markdown("---")
        sensor_dict = {
            "Nhiệt độ (temperature)": "temperature",
            "Độ ẩm (humidity)": "humidity",
            "Khoảng cách (distance_cm)": "distance_cm"
        }
        sensor_choice = st.selectbox("Chọn cảm biến cần phân tích:", list(sensor_dict.keys()))
        selected_sensor = sensor_dict[sensor_choice]

        v_c1, v_c2 = st.columns([2, 1])
        with v_c1:
            fig_out = go.Figure()
            fig_out.add_trace(go.Scatter(
                x=df_raw["timestamp"], y=df_raw[selected_sensor],
                mode="lines+markers" if len(df_raw) < 30 else "lines", name="Dữ liệu thô (Raw)",
                line=dict(color="#94A3B8", width=1.5, dash="dot")
            ))
            fig_out.add_trace(go.Scatter(
                x=df_final["timestamp"], y=df_final[selected_sensor],
                mode="lines", name="Dữ liệu sạch (Cleaned)",
                line=dict(color="#10B981", width=2.5)
            ))
            if f"{selected_sensor}_rolling_mean" in df_final.columns:
                fig_out.add_trace(go.Scatter(
                    x=df_final["timestamp"], y=df_final[f"{selected_sensor}_rolling_mean"],
                    mode="lines", name=f"Trung bình trượt (k={rolling_window})",
                    line=dict(color="#F59E0B", width=2)
                ))
            outlier_mask = df_step2.get(f"{selected_sensor}_is_outlier", pd.Series([False]*len(df_step2)))
            if outlier_mask.sum() > 0:
                fig_out.add_trace(go.Scatter(
                    x=df_raw.loc[outlier_mask, "timestamp"],
                    y=df_raw.loc[outlier_mask, selected_sensor],
                    mode="markers", name=f"Điểm ngoại lai ({outlier_mask.sum()})",
                    marker=dict(color="#EF4444", size=9, symbol="x", line=dict(width=2, color="white"))
                ))
            fig_out.update_layout(
                title=dict(text=f"Phát Hiện & Lọc Ngoại Lai ({sensor_choice} - {outlier_method})"),
                xaxis=dict(title="Thời gian"),
                yaxis=dict(title=f"Giá trị ({selected_sensor})"),
                height=390
            )
            st.plotly_chart(fig_out, use_container_width=True)

        with v_c2:
            fig_box = go.Figure()
            fig_box.add_trace(go.Box(y=df_raw[selected_sensor].dropna(), name="Thô (Raw)", marker_color="#EF4444"))
            fig_box.add_trace(go.Box(y=df_final[selected_sensor], name="Sạch (Cleaned)", marker_color="#10B981"))
            fig_box.update_layout(
                title=dict(text=f"Biểu Đồ Hộp So Sánh (Boxplot)"),
                height=390, showlegend=False
            )
            st.plotly_chart(fig_box, use_container_width=True)

        if not df_res.empty and f"{selected_sensor}_mean" in df_res.columns:
            st.markdown(f"##### Tái Lấy Mẫu (Resampling) Cửa Sổ: `{resample_window}`")
            fig_res = go.Figure()
            fig_res.add_trace(go.Scatter(
                x=df_res["timestamp"], y=df_res[f"{selected_sensor}_mean"],
                mode="lines+markers", name=f"Giá trị trung bình ({resample_window})",
                line=dict(color="#2563EB", width=2.5)
            ))
            if f"{selected_sensor}_max" in df_res.columns and f"{selected_sensor}_min" in df_res.columns:
                fig_res.add_trace(go.Scatter(
                    x=df_res["timestamp"], y=df_res[f"{selected_sensor}_max"],
                    mode="lines", name="Biên trên (Max)",
                    line=dict(color="rgba(37, 99, 235, 0.3)", width=1, dash="dash")
                ))
                fig_res.add_trace(go.Scatter(
                    x=df_res["timestamp"], y=df_res[f"{selected_sensor}_min"],
                    mode="lines", name="Biên dưới (Min)",
                    fill="tonexty", fillcolor="rgba(37, 99, 235, 0.1)",
                    line=dict(color="rgba(37, 99, 235, 0.3)", width=1, dash="dash")
                ))
            fig_res.update_layout(
                title=dict(text=f"Chuỗi Thời Gian Gom Mẫu ({sensor_choice}) Kèm Dải Min-Max Envelope"),
                xaxis=dict(title="Thời gian"),
                yaxis=dict(title=f"Giá trị ({selected_sensor})"),
                height=340
            )
            st.plotly_chart(fig_res, use_container_width=True)

        st.markdown("##### So Sánh Phương Pháp Chuẩn Hóa: Min-Max [0, 1] vs Standard Scaler")
        nc1, nc2 = st.columns(2)
        with nc1:
            if f"{selected_sensor}_minmax" in df_final.columns:
                fig_n1 = px.line(
                    df_final, x="timestamp", y=[f"{selected_sensor}_minmax"],
                    title=f"Chuẩn Hóa Min-Max [0, 1] ({sensor_choice})",
                    labels={"value": "Giá trị chuẩn hóa [0, 1]", "timestamp": "Thời gian"}
                )
                fig_n1.update_layout(height=280)
                st.plotly_chart(fig_n1, use_container_width=True)
        with nc2:
            if f"{selected_sensor}_zstandard" in df_final.columns:
                fig_n2 = px.line(
                    df_final, x="timestamp", y=[f"{selected_sensor}_zstandard"],
                    title=f"Chuẩn Hóa Standard Scaler (Mean=0, Std=1) ({sensor_choice})",
                    labels={"value": "Chỉ số Z-score", "timestamp": "Thời gian"}
                )
                fig_n2.update_layout(height=280)
                st.plotly_chart(fig_n2, use_container_width=True)

        st.markdown("##### Bảng Dữ Liệu Sau Tiền Xử Lý (10 Bản tin mới nhất)")
        st.dataframe(df_proc.tail(10), use_container_width=True)

# ================= TAB 3 =================
with tab3:
    st.markdown("##### Chỉ Số Hệ Thống & Độ Trễ Mạng End-to-End")

    metrics = {}
    if os.path.exists(config.METRICS_JSON_PATH):
        try:
            with open(config.METRICS_JSON_PATH, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception:
            metrics = {}

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: st.metric("Tổng Gói Tin Nhận", metrics.get("total_received", 0))
    with mc2: st.metric("Gói Tin Hợp Lệ", metrics.get("total_valid", 0))
    with mc3: st.metric("Tỷ Lệ Mất Gói Tin", f"{metrics.get('packet_loss_rate', 0):.1f}%")
    with mc4: st.metric("Độ Trễ Trung Bình", f"{metrics.get('average_latency_ms', 0):.0f} ms")

    st.markdown("---")
    st.markdown("##### Trạng Thái Lưu Trữ")
    dc1, dc2 = st.columns(2)
    with dc1:
        if os.path.exists(config.RAW_CSV_PATH):
            st.info(f"File CSV thô: `{config.RAW_CSV_PATH}`  |  Dung lượng: {os.path.getsize(config.RAW_CSV_PATH)/1024:.1f} KB  |  Số dòng: {len(df_raw)}")
        else:
            st.warning("File CSV thô: Chưa tìm thấy")
    with dc2:
        if os.path.exists(config.PROCESSED_CSV_PATH):
            st.info(f"File CSV tiền xử lý: `{config.PROCESSED_CSV_PATH}`  |  Dung lượng: {os.path.getsize(config.PROCESSED_CSV_PATH)/1024:.1f} KB")
        else:
            st.warning("File CSV tiền xử lý: Chưa tìm thấy")

    if "latency_ms" in df_raw.columns:
        df_lat = df_raw[df_raw["latency_ms"].notna() & (df_raw["latency_ms"] < 5000)].copy()
        if not df_lat.empty:
            st.markdown("##### Diễn Biến Độ Trễ Mạng Theo Thời Gian")
            fig_lat = px.line(df_lat, x="timestamp", y="latency_ms", color_discrete_sequence=["#8B5CF6"])
            fig_lat.update_layout(xaxis=dict(title="Thời gian"), yaxis=dict(title="Độ trễ (ms)"), height=330)
            st.plotly_chart(fig_lat, use_container_width=True)

# ================= TAB 4 =================
with tab4:
    st.markdown("##### Khám Phá & Đối Chiếu Dữ Liệu")
    cols_available = [c for c in ["temperature", "humidity", "distance_cm", "rssi", "latency_ms"] if c in df_raw.columns]
    selected_cols  = st.multiselect("Chọn các trường dữ liệu cần đối chiếu:", cols_available, default=cols_available[:2])

    if selected_cols:
        fig_exp = go.Figure()
        palette = ["#6366F1", "#F59E0B", "#10B981", "#EF4444", "#0EA5E9"]
        for i, col in enumerate(selected_cols):
            fig_exp.add_trace(go.Scatter(x=df_raw["timestamp"], y=df_raw[col],
                name=col, line=dict(color=palette[i % len(palette)], width=2)))
        fig_exp.update_layout(xaxis=dict(title="Thời gian"), yaxis=dict(title="Giá trị"),
                              legend=dict(orientation="h"), height=400)
        st.plotly_chart(fig_exp, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Xuất Dữ Liệu (Export)")
    exp1, exp2 = st.columns(2)
    with exp1:
        csv_raw = df_raw.to_csv(index=False).encode("utf-8")
        st.download_button(label="Tải File CSV Dữ Liệu Thô", data=csv_raw,
            file_name=f"raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
    with exp2:
        st.markdown(f"**Tổng số dòng:** {len(df_raw)}")
        st.markdown(f"**Các cột:** {', '.join(df_raw.columns.tolist())}")
        if not df_raw.empty:
            st.markdown(f"**Khoảng thời gian:** {df_raw['timestamp'].min()} đến {df_raw['timestamp'].max()}")
