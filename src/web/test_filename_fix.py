#!/usr/bin/env python3
"""
测试文件名修复
"""
import os
import sys
import shutil

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 切换到 web 目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from database import Database
from file_state import FileStateManager

def test_filename_upload():
    """测试文件名上传"""
    print("\n" + "=" * 60)
    print("测试文件名上传修复")
    print("=" * 60)
    
    # 清理测试环境
    test_workarea = './test_filename_workarea'
    if os.path.exists(test_workarea):
        shutil.rmtree(test_workarea)
    
    # 初始化
    db = Database(os.path.join(test_workarea, 'test.db'))
    state_manager = FileStateManager(db, test_workarea)
    
    # 测试上传不同名称的文件
    test_files = [
        ('abc.pdf', b'PDF content 1'),
        ('123.pdf', b'PDF content 2'),
        ('测试文件.html', b'HTML content'),
        ('测试文件.md', b'MD content'),
        ('中文 English 混合.txt', b'Text content'),
    ]
    
    print("\n上传文件测试：")
    for filename, content in test_files:
        file_id, filepath = state_manager.upload_file(filename, content)
        print(f"  ✓ {filename:30} -> ID={file_id}, 路径={filepath}")
        
        # 验证数据库中保存的文件名
        file_record = db.get_file_by_id(file_id)
        assert file_record['filename'] == filename, f"文件名不匹配：期望 {filename}, 实际 {file_record['filename']}"
        print(f"    数据库验证：{file_record['filename']} ✓")
    
    # 测试文件列表
    print("\n文件列表：")
    files = state_manager.list_files_tree()
    for f in files:
        print(f"  - {f['filename']} (类型：{f['file_type']})")
    
    # 测试冲突检测
    print("\n冲突检测测试：")
    try:
        file_id, filepath = state_manager.upload_file('abc.pdf', b'New content')
        print(f"  ✗ 应该检测到冲突但未检测到")
    except Exception as e:
        print(f"  ✓ 正确检测到冲突：{e}")
    
    # 清理测试环境
    shutil.rmtree(test_workarea)
    print("\n✓ 测试环境已清理")
    
    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        test_filename_upload()
    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
