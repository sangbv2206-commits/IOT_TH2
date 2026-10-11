import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None


class IoTDataPreprocessor:
    def __init__(self):
        self.influx_client = None
        self.write_api = None
        self.init_influxdb()

    def init_influxdb(self):
        if InfluxDBClient is None:
            return
        try:
            import socket
            import urllib.parse
            parsed = urllib.parse.urlparse(config.INFLUXDB_URL)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 8086
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            is_open = (s.connect_ex((host, port)) == 0)
            s.close()
            if not is_open:
                self.influx_client = None
                self.write_api = None
                return

            self.influx_client = InfluxDBClient(
                url=config.INFLUXDB_URL,
                token=config.INFLUXDB_TOKEN,
                org=config.INFLUXDB_ORG,
                timeout=1000
            )
            if self.influx_client.health().status == "pass":
                self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            else:
                self.influx_client = None
                self.write_api = None
        except Exception:
            self.influx_client = None
            self.write_api = None

    def load_raw_data(self, time_range="-1h"):
        if self.influx_client and self.write_api:
            try:
                query_api = self.influx_client.query_api()
                query = f'''
                from(bucket: "{config.INFLUXDB_BUCKET_RAW}")
                  |> range(start: {time_range})
                  |> filter(fn: (r) => r["_measurement"] == "{config.MEASUREMENT_RAW}")
                  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                  |> keep(columns: ["_time", "device_id", "temperature", "humidity", "distance_cm", "rssi", "sequence", "latency_ms"])
                '''
                df = query_api.query_data_frame(org=config.INFLUXDB_ORG, query=query)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df = df.rename(columns={"_time": "timestamp"})
                    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", utc=True)
                    return df.sort_values("timestamp").reset_index(drop=True)
            except Exception:
                pass

        if os.path.exists(config.RAW_CSV_PATH) and os.path.getsize(config.RAW_CSV_PATH) > 50:
            df = pd.read_csv(config.RAW_CSV_PATH, encoding="utf-8", encoding_errors="replace")
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", utc=True)
                df = df.sort_values("timestamp").reset_index(drop=True)
                for col in ["temperature", "humidity", "distance_cm", "rssi", "sequence", "latency_ms"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                return df

        return pd.DataFrame()

    def handle_missing_values(self, df, columns=["temperature", "humidity", "distance_cm"], method="interpolate"):
        df_clean = df.copy()
        report = {}

        for col in columns:
            if col in df_clean.columns:
                missing_count = int(df_clean[col].isna().sum())
                report[col] = missing_count
                if missing_count > 0:
                    if method == "interpolate":
                        df_clean[col] = df_clean[col].interpolate(method="linear").bfill().ffill()
                    elif method == "ffill":
                        df_clean[col] = df_clean[col].ffill().bfill()

        return df_clean, report

    def detect_outliers_iqr(self, series, factor=1.5):
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - factor * iqr
        upper_bound = q3 + factor * iqr
        outlier_mask = (series < lower_bound) | (series > upper_bound)
        return outlier_mask, lower_bound, upper_bound

    def detect_outliers_zscore(self, series, threshold=3.0):
        mean = series.mean()
        std = series.std()
        if std == 0 or np.isnan(std):
            return pd.Series([False] * len(series), index=series.index), mean, mean
        z_scores = (series - mean) / std
        outlier_mask = z_scores.abs() > threshold
        return outlier_mask, mean - threshold * std, mean + threshold * std

    def handle_outliers(self, df, columns=["temperature", "humidity", "distance_cm"], method="iqr", action="clip"):
        df_out = df.copy()
        outlier_report = {}

        for col in columns:
            if col not in df_out.columns:
                continue

            if method == "iqr":
                mask, lower, upper = self.detect_outliers_iqr(df_out[col], config.OUTLIER_CONFIG["iqr_factor"])
            else:
                mask, lower, upper = self.detect_outliers_zscore(df_out[col], config.OUTLIER_CONFIG["zscore_threshold"])

            num_outliers = int(mask.sum())
            outlier_report[col] = {
                "count": num_outliers,
                "lower_bound": float(lower),
                "upper_bound": float(upper),
                "indices": df_out.index[mask].tolist()
            }

            if num_outliers > 0:
                if action == "clip":
                    df_out[col] = df_out[col].clip(lower=lower, upper=upper)
                elif action == "interpolate":
                    df_out.loc[mask, col] = np.nan
                    df_out[col] = df_out[col].interpolate(method="linear").bfill().ffill()

            df_out[f"{col}_is_outlier"] = mask

        return df_out, outlier_report

    def resample_data(self, df, time_window="30s"):
        if df.empty or "timestamp" not in df.columns:
            return pd.DataFrame()

        df_resample = df.set_index("timestamp")
        numeric_cols = ["temperature", "humidity", "distance_cm", "rssi", "latency_ms"]
        available_cols = [c for c in numeric_cols if c in df_resample.columns]

        resampled_dfs = []
        for col in available_cols:
            agg_col = df_resample[col].resample(time_window).agg({
                f"{col}_mean": "mean",
                f"{col}_min": "min",
                f"{col}_max": "max",
                f"{col}_std": "std"
            })
            resampled_dfs.append(agg_col)

        result_df = pd.concat(resampled_dfs, axis=1).reset_index()
        return result_df.interpolate(method="linear").bfill().ffill()

    def engineer_features(self, df, columns=["temperature", "humidity", "distance_cm"], window=5):
        df_feat = df.copy()

        for col in columns:
            if col in df_feat.columns:
                df_feat[f"{col}_rolling_mean"] = df_feat[col].rolling(window=window, min_periods=1).mean()
                df_feat[f"{col}_rolling_std"] = df_feat[col].rolling(window=window, min_periods=1).std().fillna(0.0)
                df_feat[f"{col}_delta"] = df_feat[col].diff().fillna(0.0)

        return df_feat

    def normalize_features(self, df, columns=["temperature", "humidity", "distance_cm"]):
        df_norm = df.copy()

        for col in columns:
            if col in df_norm.columns:
                c_min = df_norm[col].min()
                c_max = df_norm[col].max()
                c_mean = df_norm[col].mean()
                c_std = df_norm[col].std()

                if c_max != c_min:
                    df_norm[f"{col}_minmax"] = (df_norm[col] - c_min) / (c_max - c_min)
                else:
                    df_norm[f"{col}_minmax"] = 0.5

                if c_std != 0 and not np.isnan(c_std):
                    df_norm[f"{col}_zstandard"] = (df_norm[col] - c_mean) / c_std
                else:
                    df_norm[f"{col}_zstandard"] = 0.0

        return df_norm

    def save_processed_data(self, df):
        if df.empty:
            return

        df.to_csv(config.PROCESSED_CSV_PATH, index=False)

        if self.write_api:
            try:
                for _, row in df.iterrows():
                    ts = row["timestamp"]
                    if isinstance(ts, str):
                        ts = pd.to_datetime(ts, format="ISO8601", utc=True)

                    p = (
                        Point(config.MEASUREMENT_PROCESSED)
                        .tag("device_id", "ESP32-B24DCVN086")
                        .tag("process_status", "clean")
                        .time(ts.to_pydatetime(), WritePrecision.NS)
                    )

                    numeric_cols = [c for c in df.columns if c not in ["timestamp", "device_id", "process_status", "status"]]
                    for col in numeric_cols:
                        val = row[col]
                        if pd.notna(val) and isinstance(val, (int, float, np.number)):
                            p = p.field(col, float(val))

                    self.write_api.write(bucket=config.INFLUXDB_BUCKET_PROCESSED, org=config.INFLUXDB_ORG, record=p)
            except Exception as e:
                print(f"[INFLUXDB ERROR] {e}")

    def run_full_pipeline(self, outlier_method="iqr", resample_window="30s"):
        raw_df = self.load_raw_data()
        if raw_df.empty:
            return None, {}

        df_clean, missing_report = self.handle_missing_values(raw_df)
        df_no_outliers, outlier_report = self.handle_outliers(df_clean, method=outlier_method, action="clip")
        outlier_summary = {k: v["count"] for k, v in outlier_report.items()}
        df_features = self.engineer_features(df_no_outliers, window=config.FEATURE_CONFIG["rolling_window"])
        df_normalized = self.normalize_features(df_features)
        df_resampled = self.resample_data(df_normalized, time_window=resample_window)

        self.save_processed_data(df_normalized)

        summary_metrics = {
            "total_raw_rows": len(raw_df),
            "total_processed_rows": len(df_normalized),
            "missing_values": missing_report,
            "outliers_detected": outlier_summary,
            "resampled_rows": len(df_resampled),
            "processed_time": datetime.now(timezone.utc).isoformat()
        }
        return df_normalized, summary_metrics


if __name__ == "__main__":
    preprocessor = IoTDataPreprocessor()
    preprocessor.run_full_pipeline(outlier_method="iqr", resample_window="30s")
