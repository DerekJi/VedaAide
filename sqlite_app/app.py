#!/usr/bin/env python3
"""
VedaAide SQLite Web API
简单的 Flask 应用，为 SQLite 数据库提供 HTTP 接口
"""

import sqlite3
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging

app = Flask(__name__)
CORS(app)

# 配置
DATABASE_PATH = os.getenv('DATABASE_PATH', '/app/data')
DB_FILE = os.path.join(DATABASE_PATH, 'vedaaide.db')

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 确保数据目录存在
os.makedirs(DATABASE_PATH, exist_ok=True)


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 生活事件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS life_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT NOT NULL,
            person TEXT,
            location TEXT,
            item TEXT,
            quantity REAL,
            unit TEXT,
            notes TEXT,
            raw_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 周期性事件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            person TEXT,
            location TEXT,
            category TEXT,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            recurrence_rule TEXT,
            required_items TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 向后兼容：老数据库可能缺少列，启动时自动迁移
    cursor.execute("PRAGMA table_info(life_events)")
    life_columns = {row[1] for row in cursor.fetchall()}
    if "person" not in life_columns:
        cursor.execute("ALTER TABLE life_events ADD COLUMN person TEXT")
        logger.info("Migrated life_events: added person column")
    if "location" not in life_columns:
        cursor.execute("ALTER TABLE life_events ADD COLUMN location TEXT")
        logger.info("Migrated life_events: added location column")

    cursor.execute("PRAGMA table_info(scheduled_events)")
    scheduled_columns = {row[1] for row in cursor.fetchall()}
    if "person" not in scheduled_columns:
        cursor.execute("ALTER TABLE scheduled_events ADD COLUMN person TEXT")
        logger.info("Migrated scheduled_events: added person column")
    if "location" not in scheduled_columns:
        cursor.execute("ALTER TABLE scheduled_events ADD COLUMN location TEXT")
        logger.info("Migrated scheduled_events: added location column")
    if "end_time" not in scheduled_columns:
        cursor.execute("ALTER TABLE scheduled_events ADD COLUMN end_time TIMESTAMP")
        logger.info("Migrated scheduled_events: added end_time column")
    
    # 用户背景信息表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            key TEXT PRIMARY KEY,
            value TEXT,
            is_sensitive BOOLEAN DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 背景规则表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS background_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL UNIQUE,
            description TEXT,
            rule_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


# 健康检查
@app.route('/health', methods=['GET'])
def health():
    """健康检查端点"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# 生活事件 API
@app.route('/api/life_events', methods=['GET'])
def get_life_events():
    """获取生活事件列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 支持分页
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        category = request.args.get('category', None)
        
        query = "SELECT * FROM life_events"
        params = []
        
        if category:
            query += " WHERE category = ?"
            params.append(category)
        
        query += " ORDER BY event_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'data': [dict(row) for row in rows],
            'count': len(rows),
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error fetching life events: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/life_events', methods=['POST'])
def create_life_event():
    """创建生活事件"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        data = request.json
        cursor.execute('''
            INSERT INTO life_events 
            (category, person, location, item, quantity, unit, notes, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('category'),
            data.get('person'),
            data.get('location'),
            data.get('item'),
            data.get('quantity'),
            data.get('unit'),
            data.get('notes'),
            data.get('raw_text')
        ))
        
        conn.commit()
        event_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"Created life event: {event_id}")
        return jsonify({'id': event_id, 'status': 'created'}), 201
    except Exception as e:
        logger.error(f"Error creating life event: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 周期性事件 API
@app.route('/api/scheduled_events', methods=['GET'])
def get_scheduled_events():
    """获取周期性事件列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM scheduled_events 
            ORDER BY start_time ASC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'data': [dict(row) for row in rows],
            'count': len(rows)
        })
    except Exception as e:
        logger.error(f"Error fetching scheduled events: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/scheduled_events', methods=['POST'])
def create_scheduled_event():
    """创建周期性事件"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        data = request.json
        cursor.execute('''
            INSERT INTO scheduled_events 
            (title, person, location, category, start_time, end_time, recurrence_rule, required_items, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('title'),
            data.get('person'),
            data.get('location'),
            data.get('category'),
            data.get('start_time'),
            data.get('end_time'),
            data.get('recurrence_rule'),
            json.dumps(data.get('required_items', [])),
            data.get('notes')
        ))
        
        conn.commit()
        event_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"Created scheduled event: {event_id}")
        return jsonify({'id': event_id, 'status': 'created'}), 201
    except Exception as e:
        logger.error(f"Error creating scheduled event: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 用户背景信息 API
@app.route('/api/user_profile', methods=['GET'])
def get_user_profile():
    """获取用户背景信息"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT key, value, is_sensitive FROM user_profiles')
        rows = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'data': {row['key']: row['value'] for row in rows if not row['is_sensitive']},
            'count': len(rows)
        })
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/user_profile', methods=['POST'])
def update_user_profile():
    """更新用户背景信息"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        data = request.json
        for key, value in data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles (key, value)
                VALUES (?, ?)
            ''', (key, value))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated user profile: {list(data.keys())}")
        return jsonify({'status': 'updated', 'count': len(data)})
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 背景规则 API
@app.route('/api/background_rules', methods=['GET'])
def get_background_rules():
    """获取背景规则"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM background_rules')
        rows = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'data': [dict(row) for row in rows],
            'count': len(rows)
        })
    except Exception as e:
        logger.error(f"Error fetching background rules: {str(e)}")
        return jsonify({'error': str(e)}), 500


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动应用
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('DEBUG', 'false').lower() == 'true'
    )
