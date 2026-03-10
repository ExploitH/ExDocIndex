"""
SQLite 数据库模型
用于管理文件状态、理解记录、索引记录和任务队列
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class Database:
    def __init__(self, db_path: str):
        """
        初始化数据库
        
        :param db_path: 数据库文件路径
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_tables()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_tables(self):
        """初始化所有数据表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 文件状态表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    filepath TEXT UNIQUE NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'uploaded',
                    parent_id INTEGER,
                    is_directory BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (parent_id) REFERENCES files(id) ON DELETE CASCADE
                )
            ''')
            
            # 理解记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS understanding_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id INTEGER NOT NULL,
                    summary_path TEXT,
                    status TEXT DEFAULT 'pending',
                    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_time DATETIME,
                    error_message TEXT,
                    config_snapshot TEXT,
                    FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            ''')
            
            # 索引记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS index_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    index_data TEXT,
                    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_direct_index BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            ''')
            
            # 任务队列表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    file_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_time DATETIME,
                    completed_time DATETIME,
                    error_log TEXT,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            ''')
            
            # 创建索引以优化查询
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_parent ON files(parent_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_file ON tasks(file_id)')
    
    # ========== 文件操作 ==========
    def add_file(self, filename: str, filepath: str, file_type: str, 
                 file_size: int = 0, parent_id: Optional[int] = None, 
                 is_directory: bool = False) -> int:
        """添加文件记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO files (filename, filepath, file_type, file_size, parent_id, is_directory)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (filename, filepath, file_type, file_size, parent_id, is_directory))
            return cursor.lastrowid
    
    def get_file_by_path(self, filepath: str) -> Optional[Dict]:
        """根据路径获取文件记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE filepath = ?', (filepath,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_file_by_id(self, file_id: int) -> Optional[Dict]:
        """根据 ID 获取文件记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_file_status(self, file_id: int, status: str):
        """更新文件状态"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE files SET status = ? WHERE id = ?', (status, file_id))
    
    def delete_file(self, file_id: int):
        """删除文件记录（级联删除相关记录）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
    
    def list_files(self, parent_id: Optional[int] = None) -> List[Dict]:
        """列出文件（支持按父目录过滤）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if parent_id is None:
                cursor.execute('SELECT * FROM files WHERE parent_id IS NULL ORDER BY is_directory DESC, filename')
            else:
                cursor.execute('SELECT * FROM files WHERE parent_id = ? ORDER BY is_directory DESC, filename', (parent_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_files(self) -> List[Dict]:
        """获取所有文件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM files ORDER BY upload_time DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== 理解记录操作 ==========
    def add_understanding_record(self, source_file_id: int, config_snapshot: Dict) -> int:
        """添加理解记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO understanding_records (source_file_id, config_snapshot)
                VALUES (?, ?)
            ''', (source_file_id, json.dumps(config_snapshot)))
            return cursor.lastrowid
    
    def update_understanding_record(self, record_id: int, status: str, 
                                    summary_path: Optional[str] = None,
                                    error_message: Optional[str] = None):
        """更新理解记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status == 'completed':
                cursor.execute('''
                    UPDATE understanding_records 
                    SET status = ?, summary_path = ?, completed_time = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, summary_path, record_id))
            elif status == 'failed':
                cursor.execute('''
                    UPDATE understanding_records 
                    SET status = ?, error_message = ?, completed_time = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, error_message, record_id))
            else:
                cursor.execute('''
                    UPDATE understanding_records SET status = ? WHERE id = ?
                ''', (status, record_id))
    
    def get_understanding_record(self, source_file_id: int) -> Optional[Dict]:
        """获取文件的理解记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM understanding_records 
                WHERE source_file_id = ? 
                ORDER BY created_time DESC LIMIT 1
            ''', (source_file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ========== 索引记录操作 ==========
    def add_index_record(self, file_id: int, index_data: Dict, is_direct_index: bool = False) -> int:
        """添加索引记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO index_records (file_id, index_data, is_direct_index)
                VALUES (?, ?, ?)
            ''', (file_id, json.dumps(index_data, ensure_ascii=False), is_direct_index))
            return cursor.lastrowid
    
    def update_index_record(self, file_id: int, index_data: Dict):
        """更新索引记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE index_records 
                SET index_data = ?, created_time = CURRENT_TIMESTAMP
                WHERE file_id = ?
            ''', (json.dumps(index_data, ensure_ascii=False), file_id))
    
    def get_index_record(self, file_id: int) -> Optional[Dict]:
        """获取文件的索引记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM index_records 
                WHERE file_id = ? 
                ORDER BY created_time DESC LIMIT 1
            ''', (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_index_records(self) -> List[Dict]:
        """获取所有索引记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM index_records ORDER BY created_time DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_index_record(self, file_id: int):
        """删除索引记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM index_records WHERE file_id = ?', (file_id,))
    
    # ========== 任务队列操作 ==========
    def add_task(self, task_type: str, file_id: int) -> int:
        """添加任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (task_type, file_id)
                VALUES (?, ?)
            ''', (task_type, file_id))
            return cursor.lastrowid
    
    def get_pending_tasks(self, limit: int = 1) -> List[Dict]:
        """获取待处理的任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM tasks 
                WHERE status = 'pending' 
                ORDER BY created_time ASC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def start_task(self, task_id: int):
        """开始任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks 
                SET status = 'running', started_time = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (task_id,))
    
    def complete_task(self, task_id: int, status: str = 'completed', error_log: Optional[str] = None):
        """完成任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status == 'failed':
                cursor.execute('''
                    UPDATE tasks 
                    SET status = ?, completed_time = CURRENT_TIMESTAMP, error_log = ?
                    WHERE id = ?
                ''', (status, error_log, task_id))
            else:
                cursor.execute('''
                    UPDATE tasks 
                    SET status = ?, completed_time = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, task_id))
    
    def get_task(self, task_id: int) -> Optional[Dict]:
        """获取任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_file_tasks(self, file_id: int) -> List[Dict]:
        """获取文件的所有任务"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM tasks 
                WHERE file_id = ? 
                ORDER BY created_time DESC
            ''', (file_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== 统计查询 ==========
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # 文件统计
            cursor.execute('SELECT COUNT(*) as count FROM files')
            stats['total_files'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM files WHERE status = ?', ('uploaded',))
            stats['uploaded_files'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM files WHERE status = ?', ('understood',))
            stats['understood_files'] = cursor.fetchone()['count']
            
            # 任务统计
            cursor.execute('SELECT COUNT(*) as count FROM tasks WHERE status = ?', ('pending',))
            stats['pending_tasks'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM tasks WHERE status = ?', ('running',))
            stats['running_tasks'] = cursor.fetchone()['count']
            
            return stats
