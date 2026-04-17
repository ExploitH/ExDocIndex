from fastmcp import FastMCP
import datetime,requests,os,subprocess,shutil,json
from Utils import get_index, get_doc
from dotenv import load_dotenv
# 创建一个FastMCP服务器实例
mcp = FastMCP(name="ExDocIndexMCP")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), override=False)
workdir = os.getenv('EXDOCINDEX_WORKDIR', '')
os.chdir(workdir)

@mcp.tool(
    name="get_RealTime",
    description="获取当前的精确时间（格式：YYYY-MM-DD HH:MM:SS）",
)
def get_RealTime(timezone:int=8):
    return datetime.datetime.now().astimezone(datetime.timezone(datetime.timedelta(hours=timezone))).strftime("%Y-%m-%d %H:%M:%S")


@mcp.tool(
    name="get_doc",
    description="读取文档内容",
)
def get_doc_tool(doc_path:str):
    return get_doc(doc_path)

@mcp.tool(
    name="get_index",
    description="读取索引文件",
)
def get_index_tool():
    return {"index": get_index()}

# @mcp.tool(
#     name="write_file",
#     description="写入文件内容（如果文件已存在则覆盖）",
#     output_schema={
#         "type": "object",
#         "properties": {
#             "success": {
#                 "type": "boolean",
#                 "description": "是否写入成功"
#             },
#             "message": {
#                 "type": "string",
#                 "description": "操作结果消息"
#             }
#         }
#     }
# )
# def write_file(file_path:str, content:str, encoding:str="utf-8", append:bool=False):
#     try:
#         if not os.path.isabs(file_path):
#             file_path = os.path.join(workdir, file_path)
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)
#         mode = 'a' if append else 'w'
#         with open(file_path, mode, encoding=encoding) as f:
#             f.write(content)
#         return {"success": True, "message": f"文件写入成功：{file_path}"}
#     except Exception as e:
#         return {"success": False, "message": f"写入文件失败：{e}"}


# @mcp.tool(
#     name="modify_file",
#     description="修改文件内容（查找并替换指定文本）",
#     output_schema={
#         "type": "object",
#         "properties": {
#             "success": {
#                 "type": "boolean",
#                 "description": "是否修改成功"
#             },
#             "message": {
#                 "type": "string",
#                 "description": "操作结果消息"
#             },
#             "replacements": {
#                 "type": "integer",
#                 "description": "替换的次数"
#             }
#         }
#     }
# )
# def modify_file(file_path:str, old_text:str, new_text:str, encoding:str="utf-8", replace_all:bool=True):
#     try:
#         if not os.path.isabs(file_path):
#             file_path = os.path.join(workdir, file_path)
#         with open(file_path, 'r', encoding=encoding) as f:
#             content = f.read()
#         if replace_all:
#             count = content.count(old_text)
#             new_content = content.replace(old_text, new_text)
#         else:
#             count = 1 if old_text in content else 0
#             new_content = content.replace(old_text, new_text, 1)
#         with open(file_path, 'w', encoding=encoding) as f:
#             f.write(new_content)
#         return {"success": True, "message": f"文件修改成功", "replacements": count}
#     except Exception as e:
#         return {"success": False, "message": f"修改文件失败：{e}", "replacements": 0}




# @mcp.tool(
#     name="list_directory",
#     description="列出指定路径下的文件和目录",
#     output_schema={
#         "type": "object",
#         "properties": {
#             "success": {
#                 "type": "boolean",
#                 "description": "是否列出成功"
#             },
#             "files": {
#                 "type": "array",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         "name": {
#                             "type": "string",
#                             "description": "文件/目录名"
#                         },
#                         "type": {
#                             "type": "string",
#                             "enum": ["file", "directory"],
#                             "description": "类型：文件或目录"
#                         },
#                         "size": {
#                             "type": "integer",
#                             "description": "文件大小（字节），仅文件有效"
#                         },
#                         "path": {
#                             "type": "string",
#                             "description": "完整路径"
#                         }
#                     }
#                 },
#                 "description": "文件/目录列表"
#             },
#             "message": {
#                 "type": "string",
#                 "description": "操作结果消息"
#             }
#         }
#     }
# )
# def list_directory(dir_path:str, recursive:bool=False, include_hidden:bool=False):
#     try:
#         if not os.path.isabs(dir_path):
#             dir_path = os.path.join(workdir, dir_path)
#         if not os.path.exists(dir_path):
#             return {"success": False, "files": [], "message": f"目录不存在：{dir_path}"}
#         if not os.path.isdir(dir_path):
#             return {"success": False, "files": [], "message": f"路径不是目录：{dir_path}"}
        
#         files = []
#         if recursive:
#             for root, dirs, filenames in os.walk(dir_path):
#                 if not include_hidden:
#                     dirs = [d for d in dirs if not d.startswith('.')]
#                 for name in filenames:
#                     if not include_hidden and name.startswith('.'):
#                         continue
#                     full_path = os.path.join(root, name)
#                     files.append({
#                         "name": name,
#                         "type": "file",
#                         "size": os.path.getsize(full_path),
#                         "path": full_path
#                     })
#                 for name in dirs:
#                     full_path = os.path.join(root, name)
#                     files.append({
#                         "name": name,
#                         "type": "directory",
#                         "size": 0,
#                         "path": full_path
#                     })
#         else:
#             for entry in os.listdir(dir_path):
#                 if not include_hidden and entry.startswith('.'):
#                     continue
#                 full_path = os.path.join(dir_path, entry)
#                 if os.path.isfile(full_path):
#                     files.append({
#                         "name": entry,
#                         "type": "file",
#                         "size": os.path.getsize(full_path),
#                         "path": full_path
#                     })
#                 elif os.path.isdir(full_path):
#                     files.append({
#                         "name": entry,
#                         "type": "directory",
#                         "size": 0,
#                         "path": full_path
#                     })
        
#         return {"success": True, "files": files, "message": f"列出目录成功：{dir_path}，共 {len(files)} 项"}
#     except Exception as e:
#         return {"success": False, "files": [], "message": f"列出目录失败：{e}"}


# @mcp.tool(
#     name="create_directory",
#     description="创建目录（如果目录已存在则返回提示）",
#     output_schema={
#         "type": "object",
#         "properties": {
#             "success": {
#                 "type": "boolean",
#                 "description": "是否创建成功"
#             },
#             "message": {
#                 "type": "string",
#                 "description": "操作结果消息"
#             }
#         }
#     }
# )
# def create_directory(dir_path:str):
#     try:
#         if not os.path.isabs(dir_path):
#             dir_path = os.path.join(workdir, dir_path)
#         os.makedirs(dir_path, exist_ok=True)
#         return {"success": True, "message": f"目录创建成功：{dir_path}"}
#     except Exception as e:
#         return {"success": False, "message": f"创建目录失败：{e}"}


# @mcp.tool(
#     name="delete_file_or_dir",
#     description="删除文件或目录",
#     output_schema={
#         "type": "object",
#         "properties": {
#             "success": {
#                 "type": "boolean",
#                 "description": "是否删除成功"
#             },
#             "message": {
#                 "type": "string",
#                 "description": "操作结果消息"
#             }
#         }
#     }
# )
# def delete_file_or_dir(path:str, is_directory:bool=False, recursive:bool=False):
#     try:
#         if not os.path.isabs(path):
#             path = os.path.join(workdir, path)
#         if is_directory:
#             if recursive:
#                 shutil.rmtree(path)
#             else:
#                 os.rmdir(path)
#         else:
#             os.remove(path)
#         return {"success": True, "message": f"删除成功：{path}"}
#     except Exception as e:
#         return {"success": False, "message": f"删除失败：{e}"}


# 启动服务器
if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
