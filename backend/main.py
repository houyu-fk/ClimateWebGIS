import psycopg2
import hashlib
import jwt
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ClimateWebGIS API")

class PlatformFeedback(BaseModel):
    rating: int
    feedback_text: str

# 配置跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. 数据库与全局配置
# ==========================================
DB_CONFIG = {
    "dbname": "climate_gis",
    "user": "postgres",
    "password": "1360qtip", 
    "host": "localhost",
    "port": "5432"
}

SECRET_KEY = "climate_webgis_super_secret_key"
ALGORITHM = "HS256"

def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

# ==========================================
# 2. 数据模型与认证依赖
# ==========================================
class UserAuth(BaseModel):
    username: str
    password: str

class Evaluation(BaseModel):
    station_id: str
    rating: int
    evaluation_text: str

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user_id(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或 Token 缺失")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的 Token")

# ==========================================
# 3. 气象数据接口 (地图与折线图)
# ==========================================
@app.get("/")
def read_root():
    return {"message": "欢迎来到 ClimateWebGIS 后端 API 服务"}

@app.get("/api/stations")
def get_stations():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 使用 CTE (公共表表达式) 极速计算 2024 年均温，并与站点表合并
    query = """
        WITH temp_avg AS (
            SELECT station_id, AVG(temperature) as avg_temp
            FROM weather_data
            WHERE EXTRACT(YEAR FROM obs_time) = 2024
            GROUP BY station_id
        )
        SELECT s.station_id, s.station_name, s.province, ST_AsGeoJSON(s.geom) as geometry, s.elevation_sensor, t.avg_temp
        FROM stations s
        JOIN temp_avg t ON s.station_id = t.station_id
        WHERE s.geom IS NOT NULL;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    features = []
    for row in rows:
        # 如果平均气温不为空，保留一位小数
        avg_temp = round(row[5], 1) if row[5] is not None else None
        
        feature = {
            "type": "Feature",
            "properties": {
                "station_id": row[0],
                "station_name": row[1],
                "province": row[2],
                "elevation": row[4],
                "avg_temp": avg_temp  # 将年均温传给前端
            },
            "geometry": json.loads(row[3])
        }
        features.append(feature)
        
    cursor.close()
    conn.close()
    return {"type": "FeatureCollection", "features": features}

@app.get("/api/weather/{station_id}")
def get_station_weather(station_id: str, year: int = 2024):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT obs_time, temperature, pressure, wind_speed 
        FROM weather_data 
        WHERE station_id = %s AND EXTRACT(YEAR FROM obs_time) = %s
        ORDER BY obs_time ASC;
    """
    cursor.execute(query, (station_id, year))
    rows = cursor.fetchall()
    
    times, temps, pressures, wind_speeds = [], [], [], []
    for row in rows:
        times.append(row[0].strftime("%Y-%m-%d %H:%M"))
        temps.append(row[1])
        pressures.append(row[2])
        wind_speeds.append(row[3])
        
    cursor.close()
    conn.close()
    return {
        "station_id": station_id, "times": times, "temps": temps,
        "pressures": pressures, "wind_speeds": wind_speeds
    }

# ==========================================
# 4. 用户系统接口 (注册、登录、评价)
# ==========================================
@app.post("/api/auth/register")
def register(user: UserAuth):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_pw = get_password_hash(user.password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
            (user.username, hashed_pw)
        )
        conn.commit()
        return {"message": "注册成功！请登录。"}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="用户名已存在")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/auth/login")
def login(user: UserAuth):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = %s", (user.username,))
    db_user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not db_user or db_user[1] != get_password_hash(user.password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    
    expire = datetime.utcnow() + timedelta(hours=24)
    token = jwt.encode({"sub": str(db_user[0]), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "username": user.username}

@app.post("/api/evaluations")
def create_evaluation(eval: Evaluation, user_id: str = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_evaluations (user_id, station_id, evaluation_text, rating)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, eval.station_id, eval.evaluation_text, eval.rating)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "评价发布成功！"}

@app.get("/api/evaluations/{station_id}")
def get_station_evaluations(station_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT u.username, e.rating, e.evaluation_text, e.created_at
        FROM user_evaluations e
        JOIN users u ON e.user_id = u.id
        WHERE e.station_id = %s
        ORDER BY e.created_at DESC;
    """
    cursor.execute(query, (station_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    evaluations = []
    for row in rows:
        evaluations.append({
            "username": row[0],
            "rating": row[1],
            "text": row[2],
            "time": row[3].strftime("%Y-%m-%d %H:%M")
        })
    return evaluations

# ==========================================
# 接口 7：提交对网站平台的整体评价
# ==========================================
@app.post("/api/feedback")
def submit_platform_feedback(feedback: PlatformFeedback, user_id: str = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO platform_feedback (user_id, rating, feedback_text)
        VALUES (%s, %s, %s)
        """,
        (user_id, feedback.rating, feedback.feedback_text)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "感谢您对本平台的评价！"}

# ==========================================
# 接口 8：获取系统所有评价
# ==========================================
@app.get("/api/feedback")
def get_all_platform_feedback():
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT u.username, f.rating, f.feedback_text, f.created_at
        FROM platform_feedback f
        JOIN users u ON f.user_id = u.id
        ORDER BY f.created_at DESC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    feedbacks = []
    for row in rows:
        feedbacks.append({
            "username": row[0],
            "rating": row[1],
            "text": row[2],
            "time": row[3].strftime("%Y-%m-%d %H:%M")
        })
    return feedbacks

# ==========================================
# 5. 站点管理接口 (CRUD)
# ==========================================
class StationUpdate(BaseModel):
    station_name: str
    province: str
    elevation_sensor: Optional[float] = None
    lat: float
    lon: float

class StationCreate(StationUpdate):
    station_id: str

@app.post("/api/admin/stations")
def create_station(station: StationCreate, user_id: str = Depends(get_current_user_id)):
    # 实际项目中这里可以加一个判断：是否为管理员账号。这里先简化为登录即可操作
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # PostGIS 写入点位：ST_SetSRID(ST_MakePoint(经度, 纬度), 4326)
        cursor.execute(
            """
            INSERT INTO stations (station_id, station_name, province, elevation_sensor, geom)
            VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            """,
            (station.station_id, station.station_name, station.province, station.elevation_sensor, station.lon, station.lat)
        )
        conn.commit()
        return {"message": "站点添加成功"}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="该站点ID已存在！")
    finally:
        cursor.close()
        conn.close()

@app.put("/api/admin/stations/{station_id}")
def update_station(station_id: str, station: StationUpdate, user_id: str = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE stations 
        SET station_name = %s, province = %s, elevation_sensor = %s, geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        WHERE station_id = %s
        """,
        (station.station_name, station.province, station.elevation_sensor, station.lon, station.lat, station_id)
    )
    # 检查是否真的更新到了数据
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="未找到该站点")
        
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "站点信息更新成功"}

@app.delete("/api/admin/stations/{station_id}")
def delete_station(station_id: str, user_id: str = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 级联删除保护：在删除站点前，必须先删除与之关联的气象数据和用户评价，否则会报外键约束错误
    cursor.execute("DELETE FROM user_evaluations WHERE station_id = %s", (station_id,))
    cursor.execute("DELETE FROM weather_data WHERE station_id = %s", (station_id,))
    
    cursor.execute("DELETE FROM stations WHERE station_id = %s", (station_id,))
    
    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="未找到该站点")
        
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": f"站点 {station_id} 及其关联数据已成功删除"}

# ==========================================
# 6. 用户个人中心接口
# ==========================================
class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    birth_date: Optional[str] = None
    new_password: Optional[str] = None # 用于修改密码

@app.get("/api/user/profile")
def get_profile(user_id: str = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, nickname, gender, age, location, birth_date FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="未找到用户")
        
    return {
        "username": row[0],
        "nickname": row[1] if row[1] else row[0], # 如果没有昵称，默认显示用户名
        "gender": row[2],
        "age": row[3],
        "location": row[4],
        "birth_date": str(row[5]) if row[5] else None
    }

@app.put("/api/user/profile")
def update_profile(profile: UserProfileUpdate, user_id: str = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 更新基础信息
    cursor.execute("""
        UPDATE users 
        SET nickname=%s, gender=%s, age=%s, location=%s, birth_date=%s
        WHERE id=%s
    """, (profile.nickname, profile.gender, profile.age, profile.location, profile.birth_date, user_id))
    
    # 如果用户填写了新密码，则一并更新密码
    if profile.new_password:
        hashed_pw = get_password_hash(profile.new_password)
        cursor.execute("UPDATE users SET password_hash=%s WHERE id=%s", (hashed_pw, user_id))
        
    conn.commit()
    cursor.close()
    conn.close()
    return {"message": "个人信息保存成功！"}