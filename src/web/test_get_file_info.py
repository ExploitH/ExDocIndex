#!/usr/bin/env python3
"""
测试 get_file_info 函数修复
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

def test_get_file_info():
    """测试 get_file_info 函数"""
    print("\n" + "=" * 60)
    print("测试 get_file_info 函数修复")
    print("=" * 60)
    
    # 清理测试环境
    test_workarea = './test_info_workarea'
    if os.path.exists(test_workarea):
        shutil.rmtree(test_workarea)
    
    # 初始化
    db = Database(os.path.join(test_workarea, 'test.db'))
    state_manager = FileStateManager(db, test_workarea)
    
    # 上传测试文件
    print("\n1. 上传测试文件")
    file_id, filepath = state_manager.upload_file('test.pdf', b'PDF content')
    print(f"   文件上传成功：ID={file_id}")
    
    # 测试 get_file_info
    print("\n2. 测试 get_file_info")
    file_info = state_manager.get_file_info(file_id)
    
    if file_info is None:
        print("   ✗ get_file_info 返回 None")
        return False
    
    print(f"   ✓ get_file_info 返回数据")
    print(f"     - filename: {file_info['filename']}")
    print(f"     - filepath: {file_info['filepath']}")
    print(f"     - file_type: {file_info['file_type']}")
    
    # 检查必需字段
    required_fields = [
        'is_understood',
        'is_indexed',
        'task_status',
        'task_type',
        'understanding_status',
        'summary_path'
    ]
    
    print("\n3. 检查必需字段")
    for field in required_fields:
        if field in file_info:
            print(f"   ✓ {field}: {file_info[field]}")
        else:
            print(f"   ✗ {field}: 缺失")
            return False
    
    # 验证 is_understood 初始状态
    print("\n4. 验证初始状态")
    if file_info['is_understood'] == False:
        print("   ✓ is_understood = False (正确，尚未理解)")
    else:
        print(f"   ✗ is_understood = {file_info['is_understood']} (应为 False)")
        return False
    
    if file_info['is_indexed'] == False:
        print("   ✓ is_indexed = False (正确，尚未索引)")
    else:
        print(f"   ✗ is_indexed = {file_info['is_indexed']} (应为 False)")
        return False
    
    if file_info['task_status'] is None:
        print("   ✓ task_status = None (正确，无任务)")
    else:
        print(f"   ✗ task_status = {file_info['task_status']} (应为 None)")
        return False
    
    # 清理测试环境
    shutil.rmtree(test_workarea)
    print("\n5. ✓ 测试环境已清理")
    
    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        success = test_get_file_info()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
