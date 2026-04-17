"""
异步任务队列处理器
使用后台线程处理文件理解和索引任务，防止阻塞主线程
"""
import threading
import time
import logging
import os
import sys
import json
from typing import Optional, Dict
from queue import Queue, Empty
from datetime import datetime

# 添加父目录到路径以导入其他模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from file_state import FileStateManager
from config import get_settings

logger = logging.getLogger(__name__)


class TaskProcessor:
    """任务处理器（单线程，防止爆内存）"""
    
    def __init__(self, db: Database, state_manager: FileStateManager):
        self.db = db
        self.state_manager = state_manager
        self.task_queue = Queue()
        self.running = False
        self.worker_thread = None
        self.current_task = None
        self.error_logs_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'error_logs'
        )
        os.makedirs(self.error_logs_dir, exist_ok=True)
    
    def start(self):
        """启动后台工作线程"""
        if self.running:
            logger.warning("任务处理器已在运行")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("任务处理器已启动")
    
    def stop(self):
        """停止后台工作线程"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("任务处理器已停止")
    
    def submit_task(self, task_type: str, file_id: int) -> int:
        """
        提交任务到队列
        
        :param task_type: 任务类型 ('understand' 或 'index')
        :param file_id: 文件 ID
        """
        task_id = self.db.add_task(task_type, file_id)
        self.task_queue.put(task_id)
        logger.info(f"任务已提交：类型={task_type}, 文件 ID={file_id}, 任务 ID={task_id}")
        return task_id
    
    def _worker_loop(self):
        """工作线程主循环"""
        while self.running:
            try:
                # 从队列获取任务（阻塞 1 秒）
                task_id = self.task_queue.get(timeout=1)
                
                # 获取任务信息
                task = self.db.get_task(task_id)
                if not task:
                    logger.error(f"任务不存在：ID={task_id}")
                    continue
                
                # 跳过已开始的任务
                if task['status'] != 'pending':
                    logger.warning(f"任务状态异常，跳过：ID={task_id}, 状态={task['status']}")
                    continue
                
                # 开始任务
                self.current_task = task
                self.db.start_task(task_id)
                
                try:
                    if task['task_type'] == 'understand':
                        self._process_understand_task(task_id, task['file_id'])
                    elif task['task_type'] == 'index':
                        self._process_index_task(task_id, task['file_id'])
                    else:
                        raise ValueError(f"未知任务类型：{task['task_type']}")
                    
                    # 任务完成
                    self.db.complete_task(task_id, 'completed')
                    logger.info(f"任务完成：ID={task_id}")
                    
                except Exception as e:
                    # 任务失败
                    error_msg = str(e)
                    logger.error(f"任务失败：ID={task_id}, 错误={error_msg}")
                    
                    # 保存错误日志
                    error_log_path = self._save_error_log(task_id, task, error_msg)
                    
                    # 更新任务状态
                    self.db.complete_task(task_id, 'failed', error_log_path)
                    
                    # 如果是理解任务，更新文件状态
                    if task['task_type'] == 'understand':
                        # 获取理解记录 ID（最新的理解记录）
                        with self.db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                SELECT id FROM understanding_records 
                                WHERE source_file_id = ? 
                                ORDER BY created_time DESC LIMIT 1
                            ''', (task['file_id'],))
                            row = cursor.fetchone()
                            if row:
                                record_id = row['id']
                                self.state_manager.fail_understanding(record_id, error_msg)
                
                finally:
                    self.current_task = None
                    self.task_queue.task_done()
                    
            except Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                logger.error(f"工作线程异常：{e}")
                time.sleep(1)  # 避免死循环
    
    def _process_understand_task(self, task_id: int, file_id: int):
        """
        处理理解任务
        
        :param task_id: 任务 ID
        :param file_id: 文件 ID
        """
        file_info = self.state_manager.get_file_info(file_id)
        if not file_info:
            raise ValueError(f"文件不存在：ID={file_id}")
        
        # 获取 API 配置
        config = self._load_api_config()
        
        # 开始理解
        record_id = self.state_manager.start_understanding(file_id, config)
        
        # 调用理解函数
        file_path = os.path.join(self.state_manager.workdir, file_info['filepath'])
        summary_dir = self.state_manager.summary_dir
        
        # 根据文件类型调用不同的处理函数
        try:
            if file_info['file_type'] == 'pdf':
                summary_path = self._understand_pdf(file_path, summary_dir)
            elif file_info['file_type'] == 'html':
                summary_path = self._understand_html(file_path, summary_dir)
            elif file_info['file_type'] in ['md', 'txt']:
                summary_path = self._understand_md(file_path, summary_dir)
            else:
                raise ValueError(f"不支持的文件类型：{file_info['file_type']}")
            
            # 完成理解
            self.state_manager.complete_understanding(record_id, summary_path)
            
        except Exception as e:
            # 重新抛出异常，由上层处理
            raise
    
    def _understand_pdf(self, pdf_path: str, output_dir: str) -> str:
        """理解 PDF 文件"""
        from doc_summarizer import understand_doc
        logger.info(f"开始理解 PDF: {pdf_path}")
        understand_doc(pdf_path, output_dir)
        
        # 返回生成的 MD 文件路径
        doc_name = os.path.basename(pdf_path).split('.')[0]
        summary_path = os.path.join(output_dir, f"{doc_name}.md")
        
        if not os.path.exists(summary_path):
            raise FileNotFoundError(f"理解后的文件未生成：{summary_path}")
        
        return summary_path
    
    def _understand_html(self, html_path: str, output_dir: str) -> str:
        """理解 HTML 文件"""
        from HTMLparse import parse_html
        logger.info(f"开始理解 HTML: {html_path}")
        summary_path = parse_html(html_path, output_dir)
        return summary_path
    
    def _understand_md(self, md_path: str, output_dir: str) -> str:
        """理解 MD/TXT 文件"""
        from HTMLparse import parse_md
        logger.info(f"开始理解 Markdown: {md_path}")
        summary_path = parse_md(md_path, output_dir)
        return summary_path
    
    def _process_index_task(self, task_id: int, file_id: int):
        """
        处理索引任务
        
        :param task_id: 任务 ID
        :param file_id: 文件 ID
        """
        file_info = self.state_manager.get_file_info(file_id)
        if not file_info:
            raise ValueError(f"文件不存在：ID={file_id}")
        
        # 确定使用哪个文件进行索引
        if file_info['is_understood']:
            # 使用理解后的文件
            index_file_path = file_info['summary_path']
            is_direct_index = False
        else:
            # 使用原始文件（直接索引）
            index_file_path = os.path.join(self.state_manager.workdir, file_info['filepath'])
            is_direct_index = True
        
        if not os.path.exists(index_file_path):
            raise FileNotFoundError(f"索引文件不存在：{index_file_path}")
        
        # 检查是否已存在索引（避免重复生成）
        existing_index = self.db.get_index_record(file_id)
        if existing_index and existing_index['index_data']:
            logger.info(f"文件已存在索引，跳过：ID={file_id}")
            return
        
        # 调用 gen_index 函数
        from HTMLparse import gen_index
        logger.info(f"开始生成索引：{index_file_path}")
        
        # gen_index 会直接修改 index.json
        gen_index(index_file_path, self.state_manager.index_path)
        
        # 读取索引数据并保存到数据库
        with open(self.state_manager.index_path, 'r', encoding='utf-8') as f:
            index_data_list = json.load(f)
        
        # 找到对应的索引记录
        # 对于理解后的文件，使用 summary_path 查找
        if is_direct_index:
            file_relative_path = file_info['filepath']
        else:
            file_relative_path = file_info['summary_path']
        
        index_data = None
        for item in index_data_list:
            if item['doc_path'] == file_relative_path:
                index_data = item['index']
                break
        
        if index_data:
            self.state_manager.add_to_index(file_id, index_data, is_direct_index)
            logger.info(f"索引生成成功：{file_relative_path} (直接索引={is_direct_index})")
        else:
            logger.warning(f"未找到索引数据：{file_relative_path}")
    
    def _load_api_config(self) -> Dict:
        """加载 API 配置"""
        config = get_settings()
        
        return {
            'api_key': config.get('api_key', ''),
            'base_url': config.get('base_url', ''),
            'model': config.get('model', 'qwen3.5-plus')
        }
    
    def _save_error_log(self, task_id: int, task: Dict, error_msg: str) -> str:
        """保存错误日志到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"task_{task_id}_{timestamp}.log"
        log_path = os.path.join(self.error_logs_dir, log_filename)
        
        file_info = self.state_manager.get_file_info(task['file_id'])
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"任务错误日志\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"任务 ID: {task_id}\n")
            f.write(f"任务类型：{task['task_type']}\n")
            f.write(f"文件 ID: {task['file_id']}\n")
            f.write(f"文件路径：{file_info['filepath'] if file_info else '未知'}\n")
            f.write(f"创建时间：{task['created_time']}\n")
            f.write(f"开始时间：{task['started_time']}\n")
            f.write(f"错误时间：{datetime.now().isoformat()}\n\n")
            f.write(f"错误信息:\n{error_msg}\n\n")
            f.write(f"堆栈跟踪:\n")
            
            # 如果有异常堆栈，一并记录
            import traceback
            f.write(traceback.format_exc())
        
        logger.info(f"错误日志已保存：{log_path}")
        return log_path
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        return {
            'queue_size': self.task_queue.qsize(),
            'running': self.running,
            'current_task': self.current_task,
            'worker_alive': self.worker_thread.is_alive() if self.worker_thread else False
        }


# 全局任务处理器实例
_task_processor: Optional[TaskProcessor] = None


def get_task_processor(db: Database, state_manager: FileStateManager) -> TaskProcessor:
    """获取全局任务处理器实例（单例）"""
    global _task_processor
    if _task_processor is None:
        _task_processor = TaskProcessor(db, state_manager)
        _task_processor.start()
    return _task_processor


def stop_task_processor():
    """停止全局任务处理器"""
    global _task_processor
    if _task_processor:
        _task_processor.stop()
        _task_processor = None
