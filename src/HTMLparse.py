from openai import OpenAI
import os
import logging
import json
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'), override=False)

client = OpenAI(
        api_key=os.getenv('EXDOCINDEX_LLM_API_KEY', 'sk-YOUR_API_KEY_HERE'),  # 请替换为您的 API Key
        base_url=os.getenv('EXDOCINDEX_LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
    )


def parse_html(html_path, output_dir):
    """
    解析HTML文件并将结果保存到输出文件中,输出格式为MarkDown

    :param html_path: HTML文件的路径
    :param output_dir: 输出文件的目录
    """
    SYS_PROMPT = open("agents/htmlparser.md", "r", encoding="utf-8").read()
    logger.info(f"开始解析文件: {html_path}")
    html_content = open(html_path, 'r', encoding='utf-8').read()
    completion = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": html_content}
        ],
        extra_body={"enable_thinking": True},
        stream=True,
        max_tokens=64000,
    )
    is_answering = False  # 是否进入回复阶段
    logger.info("\n" + "=" * 20 + "思考过程" + "=" * 20)
    full_text = ""
    for chunk in completion:
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                logger.info("\n" + "=" * 20 + "完整回复" + "=" * 20)
                is_answering = True
            print(delta.content, end="", flush=True)
            full_text += delta.content

    opp = f"{output_dir}/{os.path.basename(html_path).split('.')[0]}.md"
    with open(opp, "w", encoding="utf-8") as f:
        f.write(full_text)
    logger.info(f"解析完成,输出文件: {opp}")
    return opp


def parse_md(md_path, output_dir):
    """
    解析MarkDown文件并将结果保存到输出文件中,输出格式为MarkDown

    :param md_path: MarkDown文件的路径
    :param output_dir: 输出文件的目录
    """
    SYS_PROMPT = open("agents/mdparser.md", "r", encoding="utf-8").read()
    logger.info(f"开始解析文件: {md_path}")
    md_content = open(md_path, 'r', encoding='utf-8').read()
    completion = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": md_content}
        ],
        extra_body={"enable_thinking": True},
        stream=True,
        max_tokens=64000,
    )
    is_answering = False  # 是否进入回复阶段
    logger.info("\n" + "=" * 20 + "思考过程" + "=" * 20)
    full_text = ""
    for chunk in completion:
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                logger.info("\n" + "=" * 20 + "完整回复" + "=" * 20)
                is_answering = True
            print(delta.content, end="", flush=True)
            full_text += delta.content
    opp = f"{output_dir}/{os.path.basename(md_path).split('.')[0]}.md"
    with open(opp, "w", encoding="utf-8") as f:
        f.write(full_text)
    logger.info(f"解析完成,输出文件: {opp}")
    return opp

def parse_txt(doc_path: str, output_dir: str):
    """
    解析文本文件并将结果保存到输出文件中,输出格式为MarkDown

    :param doc_path: 文本文件的路径
    :param output_dir: 输出文件的目录
    """
    SYS_PROMPT = open("agents/plaintext.md", "r", encoding="utf-8").read()
    logger.info(f"开始解析文件: {doc_path}")
    txt_content = open(doc_path, 'r', encoding='utf-8').read()
    completion = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": txt_content}
        ],
        extra_body={"enable_thinking": True},
        stream=True,
        max_tokens=64000,
    )
    is_answering = False  # 是否进入回复阶段
    logger.info("\n" + "=" * 20 + "思考过程" + "=" * 20)
    full_text = ""
    for chunk in completion:
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                logger.info("\n" + "=" * 20 + "完整回复" + "=" * 20)
                is_answering = True
            print(delta.content, end="", flush=True)
            full_text += delta.content
    opp = f"{output_dir}/{os.path.basename(doc_path).split('.')[0]}.md"
    with open(opp, "w", encoding="utf-8") as f:
        f.write(full_text)
    logger.info(f"解析完成,输出文件: {opp}")
    return opp

def gen_index(doc_path: str, index_path: str, force: bool = False):
    """
    生成索引文件，索引文件的格式为 JSON

    :param doc_path: 文档的路径
    :param index_path: 索引文件的路径
    :param force: 是否强制重新生成索引（如果为 True，则覆盖已有索引）
    """
    if not os.path.isfile(index_path):
        open(index_path, 'w', encoding='utf-8').write("[]")
        index_content = []
    else:
        if os.path.getsize(index_path) == 0:
            index_content = []
        else:
            index_content = json.load(open(index_path, 'r', encoding='utf-8'))

    # 检查是否已存在索引
    existing_index = next((item for item in index_content if item["doc_path"] == doc_path), None)
    if existing_index and not force:
        logger.info(f"文档 {doc_path} 已存在索引，跳过")
        return
    elif existing_index and force:
        # 移除旧索引
        index_content = [item for item in index_content if item["doc_path"] != doc_path]
        logger.info(f"强制重新生成索引：{doc_path}")
    
    SYS_PROMPT = open("agents/librarian.md", "r", encoding="utf-8").read()
    logger.info(f"开始生成索引文件: {doc_path} -> {index_path}")
    doc_content = open(doc_path, 'r', encoding='utf-8').read()
    completion = client.chat.completions.create(
        model="qwen3.5-plus",
        messages=[
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": doc_content}
        ],
        extra_body={"enable_thinking": False},
        stream=True,
        max_tokens=64000,
    )
    is_answering = False  # 是否进入回复阶段
    logger.info("\n" + "=" * 20 + "思考过程" + "=" * 20)
    full_text = ""
    for chunk in completion:
        delta = chunk.choices[0].delta
        if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
            if not is_answering:
                print(delta.reasoning_content, end="", flush=True)
        if hasattr(delta, "content") and delta.content:
            if not is_answering:
                logger.info("\n" + "=" * 20 + "完整回复" + "=" * 20)
                is_answering = True
            print(delta.content, end="", flush=True)
            full_text += delta.content
    
    index_content.append({
        "doc_path": doc_path,
        "index": full_text
    })
    json.dump(index_content, open(index_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
    logger.info(f"索引文件 {index_path} 生成完成")
    return index_path
