#!/usr/bin/env python3
"""
ExDocIndex Web 管理系统启动脚本
"""
import os
import sys

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 切换到 web 目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import app, init_app, stop_task_processor

if __name__ == '__main__':
    try:
        print("=" * 60)
        print("ExDocIndex Web 管理系统")
        print("=" * 60)
        
        # 初始化应用
        init_app()
        
        print("\n✓ 系统初始化完成")
        print("\n访问地址：http://localhost:5000")
        print("\n按 Ctrl+C 停止服务器\n")
        print("=" * 60)
        
        # 启动服务器
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\n接收到退出信号，正在关闭...")
        stop_task_processor()
        print("✓ 服务器已关闭")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 启动失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
