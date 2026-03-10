#!/usr/bin/env python3
"""
ExDocIndex Web 管理系统测试脚本
"""
import os
import sys

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 切换到 web 目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from database import Database
from file_state import FileStateManager, FileStateError

def test_database():
    """测试数据库功能"""
    print("\n" + "=" * 60)
    print("测试数据库功能")
    print("=" * 60)
    
    # 初始化数据库
    db = Database('./test_exdocindex.db')
    print("✓ 数据库初始化成功")
    
    # 测试添加文件
    file_id = db.add_file(
        filename='test.pdf',
        filepath='InputDocs/test.pdf',
        file_type='pdf',
        file_size=1024
    )
    print(f"✓ 添加文件成功，ID={file_id}")
    
    # 测试获取文件
    file = db.get_file_by_id(file_id)
    assert file is not None
    assert file['filename'] == 'test.pdf'
    print(f"✓ 获取文件成功：{file['filename']}")
    
    # 测试更新状态
    db.update_file_status(file_id, 'understanding')
    file = db.get_file_by_id(file_id)
    assert file['status'] == 'understanding'
    print("✓ 更新文件状态成功")
    
    # 测试删除文件
    db.delete_file(file_id)
    file = db.get_file_by_id(file_id)
    assert file is None
    print("✓ 删除文件成功")
    
    # 清理测试数据库
    os.remove('./test_exdocindex.db')
    print("✓ 测试数据库已清理")
    
    return True

def test_file_state():
    """测试文件状态管理器"""
    print("\n" + "=" * 60)
    print("测试文件状态管理器")
    print("=" * 60)
    
    # 初始化
    db = Database('./test_workarea/test_exdocindex.db')
    state_manager = FileStateManager(db, './test_workarea')
    print("✓ 文件状态管理器初始化成功")
    
    # 测试上传文件
    test_content = b"This is a test file content"
    file_id, filepath = state_manager.upload_file('test.txt', test_content)
    print(f"✓ 文件上传成功，ID={file_id}, 路径={filepath}")
    
    # 测试文件列表
    files = state_manager.list_files_tree()
    assert len(files) > 0
    print(f"✓ 文件列表查询成功，共{len(files)}个文件")
    
    # 测试获取文件信息
    file_info = state_manager.get_file_info(file_id)
    assert file_info is not None
    assert file_info['filename'] == 'test.txt'
    print(f"✓ 获取文件信息成功：{file_info['filename']}")
    
    # 测试删除文件
    state_manager.delete_file(file_id)
    files = state_manager.list_files_tree()
    assert len(files) == 0
    print("✓ 文件删除成功（级联删除）")
    
    # 清理测试数据
    import shutil
    if os.path.exists('./test_workarea'):
        shutil.rmtree('./test_workarea')
    print("✓ 测试工作目录已清理")
    
    return True

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("ExDocIndex Web 管理系统 - 系统测试")
    print("=" * 60)
    
    tests = [
        ("数据库测试", test_database),
        ("文件状态管理器测试", test_file_state)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n▶ 运行测试：{test_name}")
            if test_func():
                passed += 1
                print(f"✓ {test_name} 通过")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} 失败：{e}")
            import traceback
            traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 60)
    print(f"测试完成：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
