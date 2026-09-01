from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import json
import os

# 尝试加载同目录下的 .env 文件（本地运行用；Railway 上没有该文件会自动跳过）
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

app = Flask(__name__)
CORS(app)  # 允许前端跨域请求

# ============================================================
# 阿里云 PolarDB 连接配置
# 全部从环境变量读取：
#   - 本地运行：写在项目根目录的 .env 文件里（不会提交到 GitHub）
#   - Railway： 在项目的 Variables 选项卡里配置
# ============================================================
DB_HOST = os.environ.get("DB_HOST", "ruanwork.rwlb.rds.aliyuncs.com")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

if not DB_USER or not DB_PASSWORD:
    raise RuntimeError(
        "缺少数据库账号配置：请在本目录创建 .env 文件（本地）"
        "或在 Railway 的 Variables 里配置 DB_USER 和 DB_PASSWORD"
    )

# 项目根目录（用于给手机提供网页静态文件）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10
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


# ---------- 数据库读写工具函数 ----------

def load_tasks(username):
    """读取某个用户的全部任务，返回 list"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT data FROM app_tasks WHERE username = %s", (username,))
        row = cur.fetchone()
        cur.close()
        tasks = row[0] if row and row[0] else []
        return tasks if isinstance(tasks, list) else []
    finally:
        conn.close()


def store_tasks(username, tasks):
    """整体保存某个用户的任务列表"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO app_tasks (username, data) VALUES (%s, %s)
            ON CONFLICT (username) DO UPDATE SET data = EXCLUDED.data
        ''', (username, json.dumps(tasks)))
        conn.commit()
        cur.close()
    finally:
        conn.close()


def find_task_owner(task_id):
    """在所有用户里查找某个任务 id 属于谁（DELETE 请求不带用户名，只能全局搜）"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT username, data FROM app_tasks")
        rows = cur.fetchall()
        cur.close()
        for username, data in rows:
            if isinstance(data, list):
                for t in data:
                    if str(t.get('id')) == str(task_id):
                        return username, data
        return None, None
    finally:
        conn.close()


def no_cache(resp):
    """禁止浏览器缓存接口响应，保证手机端轮询能拿到最新数据"""
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


# ================== 新版接口（对接 app.html 前端，与原 Render 后端格式一致） ==================

# 1. 获取任务列表：GET /api/tasks?user=xxx  → 直接返回任务数组
@app.route('/api/tasks', methods=['GET'])
def api_tasks_get():
    username = request.args.get('user', 'guest')
    try:
        return no_cache(jsonify(load_tasks(username)))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 2. 新增任务：POST /api/tasks  body = {id, content, timestamp, completed, username}
@app.route('/api/tasks', methods=['POST'])
def api_tasks_post():
    task = request.json
    if not task:
        return jsonify({"success": False, "error": "empty body"}), 400
    username = task.get('username', 'guest')
    try:
        tasks = load_tasks(username)
        # 避免重复添加（前端偶尔会重试）
        if not any(str(t.get('id')) == str(task.get('id')) for t in tasks):
            tasks.insert(0, task)
            store_tasks(username, tasks)
        return no_cache(jsonify({"success": True}))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 3. 更新任务：PUT /api/tasks/<id>  body = 完整 task 对象
@app.route('/api/tasks/<task_id>', methods=['PUT'])
def api_tasks_put(task_id):
    task = request.json
    if not task:
        return jsonify({"success": False, "error": "empty body"}), 400
    username = task.get('username', 'guest')
    try:
        tasks = load_tasks(username)
        found = False
        for i, t in enumerate(tasks):
            if str(t.get('id')) == str(task_id):
                tasks[i] = task
                found = True
                break
        if not found:
            # 用户名对不上时全局搜一次
            owner, owner_tasks = find_task_owner(task_id)
            if owner:
                for i, t in enumerate(owner_tasks):
                    if str(t.get('id')) == str(task_id):
                        owner_tasks[i] = task
                        found = True
                        store_tasks(owner, owner_tasks)
                        break
        else:
            store_tasks(username, tasks)
        if not found:
            return jsonify({"success": False, "error": "task not found"}), 404
        return no_cache(jsonify({"success": True}))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 4. 删除任务：DELETE /api/tasks/<id>（请求不带用户名，后端全局查找）
@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def api_tasks_delete(task_id):
    try:
        owner, owner_tasks = find_task_owner(task_id)
        if not owner:
            return jsonify({"success": False, "error": "task not found"}), 404
        owner_tasks = [t for t in owner_tasks if str(t.get('id')) != str(task_id)]
        store_tasks(owner, owner_tasks)
        return no_cache(jsonify({"success": True}))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ================== 旧版接口（保留兼容） ==================

@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
    username = request.args.get('username', 'guest')
    try:
        tasks = load_tasks(username)
        return no_cache(jsonify({"success": True, "data": tasks}))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/save_tasks', methods=['POST'])
def save_tasks():
    req = request.json
    username = req.get('username', 'guest')
    tasks = req.get('data', [])
    try:
        store_tasks(username, tasks)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ================== 静态网页服务（手机浏览器直接访问 http://电脑IP:5000 即可打开登录页） ==================

@app.route('/')
@app.route('/index.html')
def serve_index():
    return no_cache(send_from_directory(BASE_DIR, 'index.html'))


@app.route('/backend/users.json')
def serve_users():
    return no_cache(send_from_directory(os.path.join(BASE_DIR, 'backend'), 'users.json'))


@app.route('/<path:filename>')
def serve_static(filename):
    return no_cache(send_from_directory(BASE_DIR, filename))


if __name__ == '__main__':
    init_db()
    # Railway 等平台通过 PORT 环境变量指定端口；本地默认 5000
    # 监听 0.0.0.0，局域网内手机和电脑都可以访问
    port = int(os.environ.get("PORT", "5000"))
    app.run(host='0.0.0.0', port=port, debug=False)
