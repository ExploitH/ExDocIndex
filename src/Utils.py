from doc_summarizer import understand_doc, summarize_doc
import os,json

os.chdir(os.path.dirname(os.path.abspath(__file__)))
settings = {}
workdir = ""
settings_path = os.path.join(os.path.dirname(__file__), 'settings.property')
if os.path.exists(settings_path):
    with open(settings_path, 'r', encoding='utf-8') as f:
        exec(f.read())

def get_index(index_path: str="index.json"):
    """
    读取索引文件

    :param index_path: 索引文件的路径
    :return: 索引内容的列表
    """
    if not os.path.isfile(index_path):
        open(index_path, 'w', encoding='utf-8').write("")
        index_content = []
    else:
        if os.path.getsize(index_path) == 0:
            index_content = []
        else:
            index_content = json.load(open(index_path, 'r', encoding='utf-8'))
    return index_content

def get_doc(doc_path: str):
    """
    读取文档内容

    :param doc_path: 文档的路径
    :return: 文档的内容
    """
    sum_path = os.path.join(workdir, "Summary", "".join(os.path.basename(doc_path).split(".")[:-1]) + ".md")
    if not os.path.isfile(sum_path):
        if not os.path.isfile(doc_path):
            return {"success": False, "msg": "文档不存在"}
        else:
            if os.path.getsize(doc_path) == 0:
                return {"success": True, "msg": "文档为空"}
            else:
                return {"success": True, "file": open(doc_path, 'r', encoding='utf-8').read()}
    else:
        if os.path.getsize(sum_path) == 0:
            return {"success": True, "msg": "文档为空"}
        else:
            return {"success": True, "file": open(sum_path, 'r', encoding='utf-8').read()}
