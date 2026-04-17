"""
ExDocIndex Web 配置管理（dotenv）
"""
import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


WEB_DIR = Path(__file__).resolve().parent
SRC_DIR = WEB_DIR.parent
ENV_PATH = SRC_DIR / ".env"


def load_env() -> None:
    """加载 .env 配置（不覆盖已有环境变量）"""
    load_dotenv(dotenv_path=ENV_PATH, override=False)


def get_settings() -> Dict[str, str]:
    """读取运行设置（优先环境变量，其次默认值）"""
    load_env()
    return {
        "workdir": os.getenv("EXDOCINDEX_WORKDIR", "./WorkArea"),
        "api_key": os.getenv("EXDOCINDEX_LLM_API_KEY", ""),
        "base_url": os.getenv("EXDOCINDEX_LLM_BASE_URL", ""),
        "model": os.getenv("EXDOCINDEX_LLM_MODEL", "qwen3.5-plus"),
    }


def save_settings(partial: Dict[str, str]) -> Dict[str, str]:
    """
    写入 .env（仅更新 ExDocIndex 相关键）
    """
    load_env()
    current = get_settings()
    merged = {
        "workdir": partial.get("workdir", current["workdir"]),
        "api_key": partial.get("api_key", current["api_key"]),
        "base_url": partial.get("base_url", current["base_url"]),
        "model": partial.get("model", current["model"]),
    }

    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    mapping = {
        "EXDOCINDEX_WORKDIR": merged["workdir"],
        "EXDOCINDEX_LLM_API_KEY": merged["api_key"],
        "EXDOCINDEX_LLM_BASE_URL": merged["base_url"],
        "EXDOCINDEX_LLM_MODEL": merged["model"],
    }

    consumed = set()
    output_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in mapping:
            output_lines.append(f"{key}={mapping[key]}")
            consumed.add(key)
        else:
            output_lines.append(line)

    for key, value in mapping.items():
        if key not in consumed:
            output_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    return merged
