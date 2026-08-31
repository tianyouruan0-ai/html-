from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)
CORS(app)  # 开启全局跨域，允许 Vercel 前端无障碍请求

# 获取环境变量中的数据库连接地址 (Render 上的环境变量)
DATABASE_URL = os.environ.get('DATABASE_URL')


def get_db_connection():
    if not DATABASE_URL:
        return None
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


# 初始化数据库表
def init_db():
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    username TEXT,
                    text TEXT,
                    completed BOOLEAN,
                    date TEXT,
                    priority TEXT,
                    category TEXT
                )
            ''')
            conn.commit()
            cur.close()
            conn.close()
            print("数据库初始化成功！")
        except Exception as e:
            print(f"数据库初始化出错: {e}")


# 启动时自动初始化数据库
init_db()


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    user = request.args.get('user', 'guest')
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM tasks WHERE username = %s ORDER BY date DESC', (user,))
        tasks = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(tasks)
    except Exception as e:
        print(f"获取任务出错: {e}")
        return jsonify([])


@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "无数据"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "error": "数据库未连接"}), 500
    try:
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO tasks (id, username, text, completed, date, priority, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE 
            SET text = EXCLUDED.text, completed = EXCLUDED.completed, priority = EXCLUDED.priority, category = EXCLUDED.category
        ''', (
            str(data.get('id')),
            data.get('username', 'guest'),
            data.get('text', ''),
            data.get('completed', False),
            data.get('date', ''),
            data.get('priority', 'medium'),
            data.get('category', 'work')
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "task": data})
    except Exception as e:
        print(f"保存任务出错: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False}), 500
    try:
        cur = conn.cursor()
        cur.execute('DELETE FROM tasks WHERE id = %s', (str(task_id),))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"删除任务出错: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)