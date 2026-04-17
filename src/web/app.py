"""
ExDocIndex Web 管理系统
Flask 主应用
"""
from flask import Flask, render_template, request, jsonify
import os
import sys
import logging
import re
import secrets
from typing import Dict, Optional
import json

os.environ['MINERU_MODEL_SOURCE'] = 'modelscope'
# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from file_state import FileStateManager, FileStateError
from task_queue import get_task_processor, stop_task_processor
from config import get_settings, save_settings, load_env

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 Flask 应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('EXDOCINDEX_SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 最大上传 100MB

# 全局变量
db = None
state_manager = None
task_processor = None


def init_app():
    """初始化应用"""
    global db, state_manager, task_processor
    
    # 获取工作目录
    workdir = get_workdir()
    
    # 初始化数据库
    db_path = os.path.join(workdir, 'exdocindex.db')
    db = Database(db_path)
    logger.info(f"数据库初始化完成：{db_path}")
    
    # 初始化文件状态管理器
    state_manager = FileStateManager(db, workdir)
    logger.info(f"文件状态管理器初始化完成：{workdir}")
    
    # 初始化任务处理器
    task_processor = get_task_processor(db, state_manager)
    logger.info("任务处理器初始化完成")


def get_workdir() -> str:
    """从配置文件获取工作目录"""
    return get_settings().get('workdir', './WorkArea')


def get_api_config() -> dict:
    """获取 API 配置"""
    config = get_settings()
    
    return {
        'api_key': config.get('api_key', ''),
        'base_url': config.get('base_url', ''),
        'model': config.get('model', 'qwen3.5-plus')
    }


# ========== 页面路由 ==========

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/files')
def files_page():
    """文件管理页面"""
    return render_template('files.html')


@app.route('/settings')
def settings_page():
    """设置页面"""
    return render_template('settings.html')


@app.route('/qa')
def qa_page():
    """检索问答页面"""
    return render_template('qa.html')


# ========== API 路由 - 文件管理 ==========

@app.route('/api/files', methods=['GET'])
def list_files():
    """列出文件（支持树形结构）"""
    try:
        parent_path = request.args.get('parent_path', None)
        files = state_manager.list_files_tree(parent_path)
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        logger.error(f"列出文件失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/<int:file_id>', methods=['GET'])
def get_file_info(file_id):
    """获取文件详细信息"""
    try:
        file_info = state_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'file': file_info
        })
    except Exception as e:
        logger.error(f"获取文件信息失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，保留中文字符，只移除危险字符
    """
    # 保留中文、英文、数字、常见符号，移除路径分隔符等危险字符
    # 只保留文件名基本字符：字母、数字、中文、下划线、点、空格
    safe_name = re.sub(r'[^\w\u4e00-\u9fff\.\-\s]', '_', filename)
    # 替换多个连续下划线为单个
    safe_name = re.sub(r'_+', '_', safe_name)
    # 移除开头和结尾的下划线、空格
    safe_name = safe_name.strip('_ ').strip('.')
    return safe_name if safe_name else 'unnamed_file'


ALLOWED_UPLOAD_EXTENSIONS = {'pdf', 'html', 'md', 'txt'}


def validate_upload_extension(filename: str) -> bool:
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[-1].lower()
    return extension in ALLOWED_UPLOAD_EXTENSIONS


def normalize_parent_path(parent_path: Optional[str]) -> Optional[str]:
    """规范化父目录路径（仅用于拼接/查询）"""
    if not parent_path:
        return None
    normalized = os.path.normpath(parent_path).replace('\\', '/').strip('/')
    return normalized or None


def _tokenize_query(text: str) -> list:
    tokens = [t.lower() for t in re.findall(r'[\u4e00-\u9fffA-Za-z0-9_]+', text)]
    return [t for t in tokens if len(t) >= 2]


def _extract_excerpt(content: str, query_tokens: list, max_chars: int = 240) -> str:
    if not content:
        return ''
    lower_content = content.lower()
    for token in query_tokens:
        idx = lower_content.find(token.lower())
        if idx >= 0:
            start = max(0, idx - max_chars // 2)
            end = min(len(content), start + max_chars)
            return content[start:end].replace('\n', ' ')
    return content[:max_chars].replace('\n', ' ')


def _retrieve_context(question: str, top_k: int = 3) -> list:
    tokens = _tokenize_query(question)
    files = db.get_all_files()
    candidates = []

    for file_item in files:
        if file_item.get('is_directory'):
            continue
        file_info = state_manager.get_file_info(file_item['id'])
        text_parts = [
            file_item.get('filename', ''),
            file_item.get('filepath', ''),
            json.dumps(file_info.get('index_data') if file_info else None, ensure_ascii=False) if file_info else ''
        ]
        score = 0
        searchable = ' '.join(text_parts).lower()
        for token in tokens:
            score += searchable.count(token.lower())
        if score <= 0:
            continue

        source_path = None
        if file_info and file_info.get('is_understood') and file_info.get('summary_path'):
            source_path = file_info['summary_path']
        else:
            source_path = os.path.join(state_manager.workdir, file_item['filepath'])

        content = ''
        try:
            if source_path and os.path.exists(source_path):
                with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
        except Exception:
            content = ''

        candidates.append({
            'file_id': file_item['id'],
            'filename': file_item['filename'],
            'filepath': file_item['filepath'],
            'score': score,
            'content': content,
            'excerpt': _extract_excerpt(content, tokens)
        })

    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:top_k]


@app.route('/api/files/upload', methods=['POST'])
def upload_file():
    """上传文件"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            }), 400
        
        # 获取父目录路径
        parent_path = request.form.get('parent_path', None)
        
        # 清理文件名（保留中文）
        original_filename = file.filename
        filename = sanitize_filename(original_filename)

        # 确保有扩展名
        if '.' not in filename and '.' in original_filename:
            ext = original_filename.split('.')[-1]
            filename = f'{filename}.{ext}'

        if not validate_upload_extension(filename):
            return jsonify({
                'success': False,
                'error': '仅支持上传 pdf/html/md/txt 文件'
            }), 400
        
        # 检查文件名冲突
        if state_manager.check_name_conflict(filename, parent_path):
            return jsonify({
                'success': False,
                'error': f'文件 {filename} 已存在，请重命名或选择覆盖',
                'conflict': True
            }), 409
        
        # 读取文件内容
        file_content = file.read()
        
        # 上传文件
        file_id, filepath = state_manager.upload_file(filename, file_content, parent_path)
        
        logger.info(f"文件上传成功：{filepath} (ID: {file_id})")
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'file_id': file_id,
            'filepath': filepath
        })
    except FileStateError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"上传文件失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/upload', methods=['PUT'])
def overwrite_file():
    """覆盖上传同名文件"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400
        
        file = request.files['file']
        original_filename = file.filename
        filename = sanitize_filename(original_filename)
        # 确保有扩展名
        if '.' not in filename and '.' in original_filename:
            ext = original_filename.split('.')[-1]
            filename = f'{filename}.{ext}'

        if not validate_upload_extension(filename):
            return jsonify({
                'success': False,
                'error': '仅支持上传 pdf/html/md/txt 文件'
            }), 400

        parent_path = normalize_parent_path(request.form.get('parent_path', None))
        
        # 构建目标路径
        if parent_path:
            filepath = os.path.join(parent_path, filename)
        else:
            filepath = filename
        
        # 查找现有文件
        file_record = db.get_file_by_path(filepath)
        if not file_record:
            return jsonify({
                'success': False,
                'error': f'文件不存在，无法覆盖：{filename}'
            }), 404
        
        # 删除旧文件（级联删除）
        state_manager.delete_file(file_record['id'], force=True)
        
        # 上传新文件
        file_content = file.read()
        file_id, new_filepath = state_manager.upload_file(filename, file_content, parent_path)
        
        logger.info(f"文件覆盖成功：{new_filepath} (ID: {file_id})")
        return jsonify({
            'success': True,
            'message': '文件已覆盖',
            'file_id': file_id,
            'filepath': new_filepath
        })
    except Exception as e:
        logger.error(f"覆盖文件失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """删除文件（级联删除理解文件和索引）"""
    try:
        force = request.args.get('force', 'false').lower() == 'true'
        state_manager.delete_file(file_id, force=force)
        
        logger.info(f"文件删除成功：ID={file_id}")
        return jsonify({
            'success': True,
            'message': '文件已删除'
        })
    except FileStateError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"删除文件失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/directories', methods=['POST'])
def create_directory():
    """创建目录"""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': '请求体必须为 JSON 对象'
            }), 400
        dirname = data.get('dirname', '')
        parent_path = data.get('parent_path', None)
        
        if not dirname:
            return jsonify({
                'success': False,
                'error': '目录名为空'
            }), 400
        
        dir_id, dirpath = state_manager.create_directory(dirname, parent_path)
        
        logger.info(f"目录创建成功：{dirpath} (ID: {dir_id})")
        return jsonify({
            'success': True,
            'message': '目录创建成功',
            'dir_id': dir_id,
            'dirpath': dirpath
        })
    except Exception as e:
        logger.error(f"创建目录失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== API 路由 - 理解操作 ==========

@app.route('/api/files/<int:file_id>/understand', methods=['POST'])
def understand_file(file_id):
    """开始理解文件"""
    try:
        # 检查文件是否存在
        file_info = state_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 检查文件类型
        if file_info['file_type'] not in ['pdf', 'html', 'md', 'txt']:
            return jsonify({
                'success': False,
                'error': f"不支持的文件类型：{file_info['file_type']}"
            }), 400
        
        # 检查是否已理解
        if file_info['is_understood']:
            return jsonify({
                'success': False,
                'error': '文件已理解，如需重新生成请先删除原理解文件'
            }), 400
        
        # 检查是否有进行中的任务
        if file_info.get('task_status') == 'running':
            return jsonify({
                'success': False,
                'error': '文件正在理解中，请稍候'
            }), 400
        
        # 提交任务到队列
        task_id = task_processor.submit_task('understand', file_id)
        
        logger.info(f"理解任务已提交：文件 ID={file_id}")
        return jsonify({
            'success': True,
            'message': '理解任务已提交到队列',
            'task_id': task_id
        })
    except FileStateError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"理解文件失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/<int:file_id>/summary', methods=['GET'])
def get_summary(file_id):
    """获取理解后的文件内容"""
    try:
        file_info = state_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        if not file_info['is_understood']:
            return jsonify({
                'success': False,
                'error': '文件尚未理解'
            }), 400
        
        summary_path = file_info['summary_path']
        if not summary_path or not os.path.exists(summary_path):
            return jsonify({
                'success': False,
                'error': '理解文件不存在'
            }), 404
        
        # 读取文件内容
        with open(summary_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': content,
            'filepath': summary_path
        })
    except Exception as e:
        logger.error(f"获取理解文件失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== API 路由 - 索引操作 ==========

@app.route('/api/files/<int:file_id>/index', methods=['POST'])
def create_index(file_id):
    """创建索引"""
    try:
        data = request.get_json() or {}
        is_direct = data.get('is_direct', False)
        
        # 检查文件是否存在
        file_info = state_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        # 检查是否未理解且不是直接索引
        if not file_info['is_understood'] and not is_direct:
            return jsonify({
                'success': False,
                'error': '文件尚未理解，请选择"直接索引"或先理解文件',
                'require_direct_confirm': True
            }), 400
        
        # 检查是否有进行中的任务
        if file_info.get('task_status') == 'running':
            return jsonify({
                'success': False,
                'error': '文件任务正在进行中，请稍候'
            }), 400
        
        # 提交任务到队列
        task_id = task_processor.submit_task('index', file_id)
        
        logger.info(f"索引任务已提交：文件 ID={file_id} (直接索引={is_direct})")
        return jsonify({
            'success': True,
            'message': '索引任务已提交到队列',
            'task_id': task_id
        })
    except FileStateError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"创建索引失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/files/<int:file_id>/index', methods=['GET'])
def get_index(file_id):
    """获取文件的索引数据"""
    try:
        file_info = state_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        if not file_info['is_indexed']:
            return jsonify({
                'success': False,
                'error': '文件尚未索引'
            }), 404
        
        return jsonify({
            'success': True,
            'index_data': file_info['index_data'],
            'is_direct_index': file_info['is_direct_index']
        })
    except Exception as e:
        logger.error(f"获取索引失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== API 路由 - 任务状态 ==========

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    try:
        task = db.get_task(task_id)
        if not task:
            return jsonify({
                'success': False,
                'error': '任务不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'task': task
        })
    except Exception as e:
        logger.error(f"获取任务状态失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tasks/queue', methods=['GET'])
def get_queue_status():
    """获取队列状态"""
    try:
        status = task_processor.get_queue_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"获取队列状态失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== API 路由 - 统计信息 ==========

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    try:
        stats = db.get_statistics()
        queue_status = task_processor.get_queue_status()
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'queue': queue_status
        })
    except Exception as e:
        logger.error(f"获取统计信息失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== API 路由 - 设置 ==========

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """获取设置"""
    try:
        config = get_api_config()
        workdir = get_workdir()
        
        return jsonify({
            'success': True,
            'settings': {
                'workdir': workdir,
                **config
            }
        })
    except Exception as e:
        logger.error(f"获取设置失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """更新设置"""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({
                'success': False,
                'error': '请求体必须为 JSON 对象'
            }), 400
        
        save_settings({
            'api_key': data.get('llm_api_key', ''),
            'base_url': data.get('llm_base_url', ''),
            'model': data.get('llm_model', 'qwen3.5-plus')
        })
        load_env()
        
        logger.info("设置已更新")
        return jsonify({
            'success': True,
            'message': '设置已更新'
        })
    except Exception as e:
        logger.error(f"更新设置失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/qa/query', methods=['POST'])
def qa_query():
    """基于索引的检索问答"""
    try:
        data = request.get_json() or {}
        question = (data.get('question') or '').strip()
        top_k = int(data.get('top_k', 3))
        top_k = max(1, min(top_k, 5))

        if not question:
            return jsonify({'success': False, 'error': '问题不能为空'}), 400

        contexts = _retrieve_context(question, top_k=top_k)
        if not contexts:
            return jsonify({
                'success': True,
                'answer': '未在当前索引中检索到明显相关内容，请先为文档创建索引后再试。',
                'references': []
            })

        joined_context = "\n\n".join(
            f"[文档{i+1}] 文件名: {ctx['filename']}\n路径: {ctx['filepath']}\n内容片段:\n{ctx['content'][:2500]}"
            for i, ctx in enumerate(contexts)
        )

        cfg = get_api_config()
        if not cfg.get('api_key') or not cfg.get('base_url'):
            answer = '已检索到相关文档，但尚未配置 LLM API（请在设置页面填写 API Key 与 Base URL）。'
        else:
            from openai import OpenAI
            client = OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])
            completion = client.chat.completions.create(
                model=cfg['model'],
                messages=[
                    {
                        'role': 'system',
                        'content': '你是一个严谨的检索问答助手。必须仅依据给定文档片段回答；若证据不足请明确说明。'
                    },
                    {
                        'role': 'user',
                        'content': f"问题：{question}\n\n可用文档上下文：\n{joined_context}"
                    }
                ],
                temperature=0.2,
                max_tokens=1200
            )
            answer = completion.choices[0].message.content or ''

        return jsonify({
            'success': True,
            'answer': answer,
            'references': [
                {
                    'file_id': ctx['file_id'],
                    'filename': ctx['filename'],
                    'filepath': ctx['filepath'],
                    'score': ctx['score'],
                    'excerpt': ctx['excerpt']
                }
                for ctx in contexts
            ]
        })
    except Exception as e:
        logger.error(f"检索问答失败：{e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 错误处理 ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': '接口不存在'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500


# ========== 应用生命周期 ==========

@app.before_request
def before_request():
    """请求前初始化"""
    if db is None:
        init_app()


@app.teardown_appcontext
def teardown(exception):
    """应用上下文销毁时清理资源"""
    pass


# ========== 主程序入口 ==========

if __name__ == '__main__':
    try:
        init_app()
        logger.info("启动 Flask 服务器...")
        debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
        app.run(host='0.0.0.0', port=5000, debug=debug_mode, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("接收到退出信号，正在关闭...")
        stop_task_processor()
        logger.info("应用已关闭")
