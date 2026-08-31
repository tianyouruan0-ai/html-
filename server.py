from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import json

app = Flask(__name__)
CORS(app)  # 允许前端跨域请求

# 阿里云 PolarDB 连接配置（替换为你申请好的地址和账号密码）
DB_HOST = "ruanwork.rwlb.rds.aliyuncs.com"
DB_PORT = 5432
DB_NAME = "postgres"  # 默认库名，或者你创建的库
DB_USER = "你的阿里云数据库账号"
DB_PASSWORD = "你的阿里云数据库密码"


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


# 初始化建表（如果表不存在则自动创建）
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS app_tasks (
            username VARCHAR(50) PRIMARY KEY,
            data JSONB
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()


# 1. 获取任务接口
@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
    username = request.args.get('username', 'guest')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT data FROM app_tasks WHERE username = %s", (username,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        tasks = row[0] if row and row[0] else []
        return jsonify({"success": True, "data": tasks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 2. 保存任务接口
@app.route('/api/save_tasks', methods=['POST'])
def save_tasks():
    req = request.json
    username = req.get('username', 'guest')
    tasks = req.get('data', [])
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # 存在则更新，不存在则插入
        cur.execute('''
            INSERT INTO app_tasks (username, data) VALUES (%s, %s)
            ON CONFLICT (username) DO UPDATE SET data = EXCLUDED.data
        ''', (username, json.dumps(tasks)))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    init_db()
    # 局域网内手机和电脑都可以访问（监听 0.0.0.0）
    app.run(host='0.0.0.0', port=5000, debug=True)