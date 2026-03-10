from PDFparse import parse_doc as pdfparse
from HTMLparse import parse_html, parse_md, parse_txt, gen_index
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)



def understand_doc(doc_path: str, output_dir: str):
    """
    对文档进行理解并将结果保存到输出文件中,输出格式为MarkDown

    :param doc_path: 文档的路径
    :param output_dir: 输出文件的目录
    """
    if doc_path.endswith('.pdf'):
        doc_name = os.path.basename(doc_path).split('.')[0]
        pdfparse([doc_path], output_dir='./cache', backend='pipeline')
        summary_path = os.path.abspath(os.path.join('./cache', f"{doc_name}/auto/{doc_name}.md"))
        parse_md(summary_path, output_dir)
    elif doc_path.endswith('.html'):
        parse_html(doc_path, output_dir)
    elif doc_path.endswith('.md'):
        parse_md(doc_path, output_dir)
    elif doc_path.endswith('.txt'):
        parse_txt(doc_path, output_dir)
    else:
        logger.error(f"不支持的文档格式: {doc_path}")

def summarize_doc(doc_path: str, index_path: str):
    """
    对文档进行总结并将结果保存到输出文件中,输出格式为MarkDown

    :param doc_path: 文档的路径
    :param index_path: 索引文件的路径
    """
    gen_index(doc_path, index_path)