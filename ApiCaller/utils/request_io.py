"""请求配置读取与请求体序列化辅助函数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_json_file(file_path: str) -> Dict[str, Any]:
    """读取 JSON 文件并返回字典对象。

    参数:
        file_path (str): JSON 文件路径。

    返回:
        Dict[str, Any]: 解析后的字典对象。
    """
    with Path(file_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def dump_pretty_json(data: Any) -> str:
    """将对象格式化为便于查看的 JSON 字符串。

    参数:
        data (Any): 待序列化对象。

    返回:
        str: 格式化后的 JSON 字符串。
    """
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
