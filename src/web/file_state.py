"""
文件状态管理器
负责管理文件的完整生命周期，包括上传、理解、索引、删除等操作的强关联约束
"""
import os
import shutil
import json
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from database import Database

logger = logging.getLogger(__name__)


class FileStateError(Exception):
    """文件状态操作异常"""
    pass


class FileStateManager:
    def __init__(self, db: Database, workdir: str):
        """
        初始化文件状态管理器
        
        :param db: 数据库实例
        :param workdir: 工作目录路径
        """
        self.db = db
        self.workdir = workdir
        self.input_docs_dir = os.path.join(workdir, 'InputDocs')
        self.summary_dir = os.path.join(workdir, 'Summary')
        self.index_path = os.path.join(workdir, 'index.json')
        
        # 确保目录存在
        os.makedirs(self.input_docs_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)
        
        # 初始化索引文件
        if not os.path.exists(self.index_path):
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
    
    def _get_relative_path(self, absolute_path: str) -> str:
        """获取相对于 workdir 的相对路径"""
        return os.path.relpath(absolute_path, self.workdir)
    
    def _get_absolute_path(self, relative_path: str) -> str:
        """获取绝对路径"""
        return os.path.normpath(os.path.join(self.workdir, relative_path))

    def _validate_parent_path(self, parent_path: Optional[str]) -> Optional[str]:
        """验证并规范化 parent_path，阻止路径穿越"""
        if parent_path is None:
            return None
        normalized = os.path.normpath(parent_path).replace('\\', '/').strip('/')
        if normalized in ('', '.'):
            return None
        if normalized.startswith('..') or '/..' in normalized:
            raise FileStateError("非法父目录路径")
        return normalized

    def _safe_join_under_input_docs(self, *parts: str) -> str:
        """安全拼接路径，确保目标路径始终在 InputDocs 内"""
        candidate = os.path.normpath(os.path.join(self.input_docs_dir, *parts))
        input_docs_abs = os.path.abspath(self.input_docs_dir)
        candidate_abs = os.path.abspath(candidate)
        if os.path.commonpath([candidate_abs, input_docs_abs]) != input_docs_abs:
            raise FileStateError("非法路径访问")
        return candidate
    
    # ========== 文件上传 ==========
    def upload_file(self, filename: str, file_content: bytes, 
                    parent_path: Optional[str] = None) -> Tuple[int, str]:
        """
        上传文件
        
        :param filename: 文件名
        :param file_content: 文件内容（字节）
        :param parent_path: 父目录相对路径（可选）
        :return: (file_id, relative_path)
        :raises FileStateError: 如果文件已存在
        """
        # 构建目标路径
        normalized_parent = self._validate_parent_path(parent_path)
        if normalized_parent:
            target_dir = self._safe_join_under_input_docs(normalized_parent)
            relative_path = os.path.join(normalized_parent, filename)
        else:
            target_dir = self.input_docs_dir
            relative_path = filename

        target_path = self._safe_join_under_input_docs(relative_path)
        
        # 检查是否已存在
        if os.path.exists(target_path):
            raise FileStateError(f"文件已存在：{relative_path}")
        
        # 确保目录存在
        os.makedirs(target_dir, exist_ok=True)
        
        # 写入文件
        with open(target_path, 'wb') as f:
            f.write(file_content)
        
        # 获取文件信息
        file_size = os.path.getsize(target_path)
        file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
        
        # 获取父目录 ID
        parent_id = None
        if normalized_parent:
            parent_file = self.db.get_file_by_path(normalized_parent)
            if parent_file:
                parent_id = parent_file['id']
        
        # 添加到数据库
        file_id = self.db.add_file(
            filename=filename,
            filepath=self._get_relative_path(target_path),
            file_type=file_type,
            file_size=file_size,
            parent_id=parent_id,
            is_directory=False
        )
        
        logger.info(f"文件上传成功：{relative_path} (ID: {file_id})")
        return file_id, self._get_relative_path(target_path)
    
    def create_directory(self, dirname: str, parent_path: Optional[str] = None) -> Tuple[int, str]:
        """
        创建目录
        
        :param dirname: 目录名
        :param parent_path: 父目录相对路径（可选）
        :return: (dir_id, relative_path)
        """
        normalized_parent = self._validate_parent_path(parent_path)
        if normalized_parent:
            target_dir = self._safe_join_under_input_docs(normalized_parent, dirname)
            relative_path = os.path.join(normalized_parent, dirname)
        else:
            target_dir = self._safe_join_under_input_docs(dirname)
            relative_path = dirname
        
        # 创建目录
        os.makedirs(target_dir, exist_ok=True)
        
        # 获取父目录 ID
        parent_id = None
        if normalized_parent:
            parent_file = self.db.get_file_by_path(normalized_parent)
            if parent_file:
                parent_id = parent_file['id']
        
        # 添加到数据库
        dir_id = self.db.add_file(
            filename=dirname,
            filepath=self._get_relative_path(target_dir),
            file_type='directory',
            file_size=0,
            parent_id=parent_id,
            is_directory=True
        )
        
        logger.info(f"目录创建成功：{relative_path} (ID: {dir_id})")
        return dir_id, self._get_relative_path(target_dir)
    
    # ========== 文件删除（级联删除） ==========
    def delete_file(self, file_id: int, force: bool = False) -> bool:
        """
        删除文件（级联删除理解文件和索引）
        
        :param file_id: 文件 ID
        :param force: 是否强制删除（即使有理解文件）
        :return: 是否删除成功
        """
        file_record = self.db.get_file_by_id(file_id)
        if not file_record:
            raise FileStateError(f"文件不存在：ID={file_id}")
        
        # 如果是目录，递归删除
        if file_record['is_directory']:
            return self._delete_directory(file_id, force)
        
        # 检查是否有理解文件
        understanding_record = self.db.get_understanding_record(file_id)
        if understanding_record and understanding_record['status'] == 'completed':
            if not force:
                # 删除理解文件
                summary_path = understanding_record['summary_path']
                if summary_path and os.path.exists(summary_path):
                    os.remove(summary_path)
                    logger.info(f"级联删除理解文件：{summary_path}")
            
            # 删除理解记录
            self.db.delete_index_record(file_id)
        
        # 删除索引记录
        self.db.delete_index_record(file_id)
        
        # 删除物理文件
        file_path = self._get_absolute_path(file_record['filepath'])
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"删除物理文件：{file_path}")
        
        # 从数据库删除
        self.db.delete_file(file_id)
        
        # 从索引文件中移除
        self._remove_from_index(file_record['filepath'])
        
        logger.info(f"文件删除成功：{file_record['filepath']}")
        return True
    
    def _delete_directory(self, dir_id: int, force: bool = False) -> bool:
        """递归删除目录"""
        dir_record = self.db.get_file_by_id(dir_id)
        if not dir_record:
            raise FileStateError(f"目录不存在：ID={dir_id}")
        
        # 获取目录下所有文件
        child_files = self.db.list_files(parent_id=dir_id)
        
        # 递归删除所有子文件
        for child in child_files:
            self.delete_file(child['id'], force)
        
        # 删除物理目录
        dir_path = self._get_absolute_path(dir_record['filepath'])
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            logger.info(f"删除物理目录：{dir_path}")
        
        # 从数据库删除
        self.db.delete_file(dir_id)
        
        logger.info(f"目录删除成功：{dir_record['filepath']}")
        return True
    
    # ========== 文件理解 ==========
    def start_understanding(self, file_id: int, config: Dict) -> int:
        """
        开始理解文件
        
        :param file_id: 文件 ID
        :param config: API 配置
        :return: 理解记录 ID
        """
        file_record = self.db.get_file_by_id(file_id)
        if not file_record:
            raise FileStateError(f"文件不存在：ID={file_id}")
        
        # 检查文件类型
        if file_record['file_type'] not in ['pdf', 'html', 'md', 'txt']:
            raise FileStateError(f"不支持的文件类型：{file_record['file_type']}")
        
        # 检查是否已有理解记录
        existing_record = self.db.get_understanding_record(file_id)
        if existing_record and existing_record['status'] == 'completed':
            # 检查理解文件是否存在
            if existing_record['summary_path'] and os.path.exists(existing_record['summary_path']):
                raise FileStateError(f"文件已理解，如需重新生成请先删除原理解文件")
        
        # 更新文件状态
        self.db.update_file_status(file_id, 'understanding')
        
        # 创建理解记录
        record_id = self.db.add_understanding_record(file_id, config)
        
        logger.info(f"开始理解文件：{file_record['filepath']} (记录 ID: {record_id})")
        return record_id
    
    def complete_understanding(self, record_id: int, summary_path: str):
        """
        完成理解
        
        :param record_id: 理解记录 ID
        :param summary_path: 理解文件路径
        """
        record = self.db.get_understanding_record(0)  # 临时获取，实际应该用 record_id 查询
        
        # 由于数据库设计问题，这里需要通过 record_id 反推 source_file_id
        # 简化处理：直接更新记录
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE understanding_records 
                SET status = 'completed', summary_path = ?, completed_time = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (summary_path, record_id))
        
        # 获取源文件 ID
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT source_file_id FROM understanding_records WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            if row:
                file_id = row['source_file_id']
                self.db.update_file_status(file_id, 'understood')
        
        logger.info(f"理解完成：{summary_path}")
    
    def fail_understanding(self, record_id: int, error_message: str):
        """
        标记理解为失败
        
        :param record_id: 理解记录 ID
        :param error_message: 错误信息
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE understanding_records 
                SET status = 'failed', error_message = ?, completed_time = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (error_message, record_id))
        
        # 获取源文件 ID 并更新状态
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT source_file_id FROM understanding_records WHERE id = ?', (record_id,))
            row = cursor.fetchone()
            if row:
                file_id = row['source_file_id']
                self.db.update_file_status(file_id, 'failed')
        
        logger.error(f"理解失败：记录 ID={record_id}, 错误={error_message}")
    
    def get_summary_path(self, file_id: int) -> Optional[str]:
        """获取文件的理解文件路径"""
        record = self.db.get_understanding_record(file_id)
        if record and record['status'] == 'completed':
            return record['summary_path']
        return None
    
    def is_understood(self, file_id: int) -> bool:
        """检查文件是否已理解"""
        summary_path = self.get_summary_path(file_id)
        return summary_path is not None and os.path.exists(summary_path)
    
    # ========== 索引管理 ==========
    def add_to_index(self, file_id: int, index_data: Dict, is_direct_index: bool = False) -> bool:
        """
        添加到索引
        
        :param file_id: 文件 ID
        :param index_data: 索引数据（JSON 格式）
        :param is_direct_index: 是否为直接索引（未理解文件）
        """
        file_record = self.db.get_file_by_id(file_id)
        if not file_record:
            raise FileStateError(f"文件不存在：ID={file_id}")
        
        # 检查是否已有索引
        existing_index = self.db.get_index_record(file_id)
        if existing_index:
            # 更新现有索引
            self.db.update_index_record(file_id, index_data)
        else:
            # 添加新索引
            self.db.add_index_record(file_id, index_data, is_direct_index)
        
        # 同步到 index.json 文件
        self._sync_index_to_file()
        
        logger.info(f"索引添加成功：{file_record['filepath']} (直接索引={is_direct_index})")
        return True
    
    def _sync_index_to_file(self):
        """同步数据库索引到 index.json 文件"""
        index_records = self.db.get_all_index_records()
        
        index_data = []
        for record in index_records:
            try:
                index_content = json.loads(record['index_data'])
                file_record = self.db.get_file_by_id(record['file_id'])
                if file_record:
                    index_data.append({
                        'doc_path': file_record['filepath'],
                        'index': index_content
                    })
            except Exception as e:
                logger.error(f"索引数据解析失败：{record['id']}, 错误：{e}")
        
        # 写入文件
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"索引文件同步完成：{self.index_path}")
    
    def _remove_from_index(self, filepath: str):
        """从索引中移除文件"""
        try:
            # 读取现有索引
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 过滤掉要删除的文件
            index_data = [item for item in index_data if item['doc_path'] != filepath]
            
            # 写回文件
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"从索引中移除：{filepath}")
        except Exception as e:
            logger.error(f"从索引移除失败：{filepath}, 错误：{e}")
    
    # ========== 文件列表 ==========
    def list_files_tree(self, parent_path: Optional[str] = None) -> List[Dict]:
        """
        列出文件树
        
        :param parent_path: 父目录路径（None 表示根目录）
        :return: 文件列表
        """
        parent_id = None
        normalized_parent = self._validate_parent_path(parent_path)
        if normalized_parent:
            parent_file = self.db.get_file_by_path(normalized_parent)
            if parent_file:
                parent_id = parent_file['id']
        
        files = self.db.list_files(parent_id=parent_id)
        
        # 增强文件信息
        for file in files:
            # 添加理解状态
            file['is_understood'] = self.is_understood(file['id'])
            
            # 添加索引状态
            index_record = self.db.get_index_record(file['id'])
            file['is_indexed'] = index_record is not None
            
            # 添加任务状态
            tasks = self.db.get_file_tasks(file['id'])
            if tasks:
                latest_task = tasks[0]
                file['task_status'] = latest_task['status']
                file['task_type'] = latest_task['task_type']
            else:
                file['task_status'] = None
                file['task_type'] = None
        
        return files
    
    def get_file_info(self, file_id: int) -> Optional[Dict]:
        """获取文件完整信息"""
        file_record = self.db.get_file_by_id(file_id)
        if not file_record:
            return None
        
        # 添加理解状态
        file_record['is_understood'] = self.is_understood(file_id)
        
        # 添加理解信息
        understanding_record = self.db.get_understanding_record(file_id)
        file_record['understanding_status'] = understanding_record['status'] if understanding_record else None
        file_record['understanding_error'] = understanding_record['error_message'] if understanding_record else None
        file_record['summary_path'] = understanding_record['summary_path'] if understanding_record else None
        
        # 添加索引信息
        index_record = self.db.get_index_record(file_id)
        file_record['is_indexed'] = index_record is not None
        file_record['index_data'] = json.loads(index_record['index_data']) if index_record and index_record['index_data'] else None
        file_record['is_direct_index'] = index_record['is_direct_index'] if index_record else False
        
        # 添加任务状态
        tasks = self.db.get_file_tasks(file_id)
        file_record['task_history'] = tasks
        if tasks:
            latest_task = tasks[0]
            file_record['task_status'] = latest_task['status']
            file_record['task_type'] = latest_task['task_type']
        else:
            file_record['task_status'] = None
            file_record['task_type'] = None
        
        return file_record
    
    def check_name_conflict(self, filename: str, parent_path: Optional[str] = None) -> bool:
        """检查文件名冲突"""
        normalized_parent = self._validate_parent_path(parent_path)
        if normalized_parent:
            relative_path = os.path.join(normalized_parent, filename)
        else:
            relative_path = filename

        target_path = self._safe_join_under_input_docs(relative_path)
        return os.path.exists(target_path)
