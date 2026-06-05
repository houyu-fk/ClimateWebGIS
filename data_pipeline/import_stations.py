import pandas as pd
import psycopg2
import os

# 数据库连接配置 (请替换为你自己的密码)
DB_CONFIG = {
    "dbname": "climate_gis",
    "user": "postgres",
    "password": "1360qtip",
    "host": "localhost",
    "port": "5432"
}

# 项目目录
DATA_DIR = r"D:\university_documents\2025-2026学习资料\WebGIS\ClimateWebGIS\ClimateWebGIS\data"

def import_stations():
    csv_path = os.path.join(DATA_DIR, "stations_china.csv")
    
    # 根据你实际转出来的 CSV 列名进行调整
    # 假设列名为：省份, 区站号, 站名, 纬度, 经度, 气压传感器拔海高度, 观测场拔海高度
    df = pd.read_csv(csv_path,encoding='gbk')
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for index, row in df.iterrows():
        station_id = str(row['区站号'])
        # 假设原始数据是 11662，这里除以 100 转换为 116.62
        lon = float(row['经度']) / 100.0  
        lat = float(row['纬度']) / 100.0
        
        # 构造 PostGIS 识别的 WKT (Well-Known Text) 格式
        geom_wkt = f"SRID=4326;POINT({lon} {lat})"
        
        insert_sql = """
            INSERT INTO stations (station_id, station_name, province, latitude, longitude, geom, elevation_sensor, elevation_obser)
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromEWKT(%s), %s, %s)
            ON CONFLICT (station_id) DO NOTHING;
        """
# 1. 提取高度数据，并用 replace 把双减号 '--' 替换为正常的单减号 '-'
        sensor_alt_str = str(row['气压传感器拔海高度(米)']).replace('--', '-')
        obser_alt_str = str(row['观测场拔海高度(米)']).replace('--', '-')
        
        # 2. 安全转换为浮点数（如果数据是空的，Pandas 会将其读为 'nan'，需要转成 None 以便存入数据库的 NULL）
        sensor_alt = float(sensor_alt_str) if sensor_alt_str != 'nan' and sensor_alt_str.strip() != '' else None
        obser_alt = float(obser_alt_str) if obser_alt_str != 'nan' and obser_alt_str.strip() != '' else None

        # 3. 构造 PostGIS 识别的 WKT (Well-Known Text) 格式
        geom_wkt = f"SRID=4326;POINT({lon} {lat})"
        
        insert_sql = """
            INSERT INTO stations (station_id, station_name, province, latitude, longitude, geom, elevation_sensor, elevation_obser)
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromEWKT(%s), %s, %s)
            ON CONFLICT (station_id) DO NOTHING;
        """
        
        # 4. 执行 SQL，使用清洗干净的 sensor_alt 和 obser_alt
        cursor.execute(insert_sql, (
            station_id, row['站名'], row['省份'], 
            lat, lon, geom_wkt, 
            sensor_alt, obser_alt
        ))
    
    conn.commit()
    cursor.close()
    conn.close()
    print("站点数据入库完毕！")

if __name__ == "__main__":
    import_stations()