import pandas as pd
import psycopg2
import glob
import os
import io

DB_CONFIG = {
    "dbname": "climate_gis",
    "user": "postgres",
    "password": "1360qtip",
    "host": "localhost",
    "port": "5432"
}

DATA_DIR = r"D:\university_documents\2025-2026学习资料\WebGIS\ClimateWebGIS\ClimateWebGIS\data"

def process_and_copy_data(year):
    folder_path = os.path.join(DATA_DIR, str(year))
    files = glob.glob(f"{folder_path}/*.gz")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    for file in files:
        station_id = os.path.basename(file).split('-')[0][:5]
        
        # NCDC 数据以多空格分隔
        df = pd.read_csv(file, compression='gzip', sep=r'\s+', header=None,
                         names=['year', 'month', 'day', 'hour', 'temp', 'dew', 
                                'slp', 'wind_dir', 'wind_speed', 'sky', 'precip1', 'precip6'])
        
        # 1. 解决时区问题：NCDC是UTC时间，加8小时转为北京时间
        df['obs_time'] = pd.to_datetime(df[['year', 'month', 'day', 'hour']]) + pd.Timedelta(hours=8)
        
        # 2. 数据缩放因子还原 (除以10)，缺测值 -9999 替换为空
        df.replace(-9999, None, inplace=True)
        df['temp'] = df['temp'].astype(float) / 10.0
        df['dew'] = df['dew'].astype(float) / 10.0
        df['slp'] = df['slp'].astype(float) / 10.0
        df['wind_speed'] = df['wind_speed'].astype(float) / 10.0
        df['precip1'] = df['precip1'].astype(float) / 10.0
        
        df['station_id'] = station_id
        
        # 提取需要入库的列
        cols_to_db = ['station_id', 'obs_time', 'temp', 'dew', 'slp', 'wind_dir', 'wind_speed', 'precip1']
        df_db = df[cols_to_db].copy()
        
        # 3. 高性能批量写入准备 (CSV 内存缓冲区)
        csv_buffer = io.StringIO()
        df_db.to_csv(csv_buffer, index=False, header=False, na_rep='')
        csv_buffer.seek(0)
        
        try:
            # 使用 PostgreSQL 原生的 COPY 进行极速插入
            cursor.copy_expert(
                "COPY weather_data (station_id, obs_time, temperature, dew_point, pressure, wind_dir, wind_speed, precip_1h) FROM STDIN WITH CSV",
                csv_buffer
            )
            conn.commit()
            print(f"[{year}] 站点 {station_id} 共 {len(df_db)} 条记录极速入库成功。")
        except Exception as e:
            conn.rollback()
            print(f"站点 {station_id} 入库失败: {e}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    # 测试运行 2023 年的数据
    process_and_copy_data(2025)