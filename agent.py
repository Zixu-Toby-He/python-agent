"""一个只提供 ``utils/操作.py`` 中文件与 PowerShell 操作的轻量级 Agent。

API 地址和模型按需求固定；API 密钥从 ``DEEPSEEK_API_KEY`` 环境变量读取，
避免把密钥写进源代码。脚本只依赖 Python 标准库。
"""

from __future__ import annotations

import json
import os
try:
    import tkinter as tk
except ImportError:
    tk = None
_TkError = tk.TclError if tk is not None else RuntimeError
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from utils.操作 import (
    分字符读取文件,
    分行读取文件,
    写入文件,
    新建文件夹,
    执行powershell命令,
    读取文件,
)


DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"
最大对话轮数 = 8


def 弹窗询问(问题: str, 标题: str = "需要确认") -> str:
    """用弹窗获取不明确操作的补充信息；无图形环境时退回终端输入。"""
    try:
        if tk is None:
            raise RuntimeError("当前 Python 未安装 tkinter")
        根窗口 = tk.Tk()
        根窗口.withdraw()
        对话框 = tk.Toplevel(根窗口)
        对话框.title(标题)
        对话框.resizable(False, False)
        tk.Label(对话框, text=问题, padx=16, pady=12, justify="left").pack()
        输入框 = tk.Entry(对话框, width=64)
        输入框.pack(padx=16, pady=(0, 12))
        输入框.focus_set()
        返回值 = {"内容": ""}

        def 确定() -> None:
            返回值["内容"] = 输入框.get().strip()
            对话框.destroy()

        tk.Button(对话框, text="确定", command=确定, width=10).pack(pady=(0, 12))
        对话框.protocol("WM_DELETE_WINDOW", 确定)
        根窗口.wait_window(对话框)
        根窗口.destroy()
        return 返回值["内容"]
    except (_TkError, RuntimeError):
        return input(f"{问题}\n> ").strip()


工具函数: dict[str, Callable[..., Any]] = {
    "create_directory": 新建文件夹,
    "write_file": 写入文件,
    "read_file": 读取文件,
    "read_file_lines": 分行读取文件,
    "read_file_chars": 分字符读取文件,
    "run_powershell": 执行powershell命令,
}

工具显示名称 = {
    "create_directory": "新建文件夹",
    "write_file": "写入文件",
    "read_file": "读取文件",
    "read_file_lines": "按行读取文件",
    "read_file_chars": "按字符读取文件",
    "run_powershell": "执行 PowerShell 命令",
}


def _输出进度(消息: str) -> None:
    print(f"\n[Agent] {消息}", flush=True)


def _参数摘要(参数: dict[str, Any], 最大长度: int = 600) -> str:
    摘要 = json.dumps(参数, ensure_ascii=False, sort_keys=True, default=str)
    if len(摘要) > 最大长度:
        return 摘要[:最大长度] + "..."
    return 摘要

工具定义 = [
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "新建文件夹（会先征得用户同意）",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "以 UTF-8 覆盖写入文件（会先征得用户同意）",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取不超过 100000 字符的 UTF-8 文件",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "encoding": {"type": "string", "default": "utf-8"}}, "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_lines",
            "description": "按 [起始行, 终止行]（终止位置不含）读取一个或多个行区间",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "ranges": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}}, "encoding": {"type": "string", "default": "utf-8"}}, "required": ["path", "ranges"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_chars",
            "description": "按 [起始字符, 终止字符]（终止位置不含）读取一个或多个字符区间",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "ranges": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}}, "encoding": {"type": "string", "default": "utf-8"}}, "required": ["path", "ranges"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_powershell",
            "description": "执行 PowerShell 命令；必须说明命令功能，并会先征得用户同意",
            "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "purpose": {"type": "string"}}, "required": ["command", "purpose"]},
        },
    },
]


def _转为操作参数(工具名: str, 参数: dict[str, Any]) -> dict[str, Any]:
    """校验并把模型使用的英文参数映射到操作.py 的中文签名。"""
    需要 = {
        "create_directory": ("path",),
        "write_file": ("path", "content"),
        "read_file": ("path",),
        "read_file_lines": ("path", "ranges"),
        "read_file_chars": ("path", "ranges"),
        "run_powershell": ("command", "purpose"),
    }[工具名]
    for 键 in 需要:
        while 键 not in 参数 or 参数[键] in (None, ""):
            答案 = 弹窗询问(f"操作 {工具名} 缺少参数 {键}，请输入它的值。")
            if not 答案:
                raise ValueError(f"用户未提供必要参数：{键}")
            if 键 == "ranges":
                try:
                    参数[键] = json.loads(答案)
                except json.JSONDecodeError as 异常:
                    raise ValueError("ranges 必须是 JSON，例如 [[0, 10]]") from 异常
            else:
                参数[键] = 答案
    if 工具名 in ("read_file_lines", "read_file_chars"):
        范围 = 参数["ranges"]
        if not isinstance(范围, list) or any(not isinstance(项, (list, tuple)) or len(项) != 2 for 项 in 范围):
            raise ValueError("ranges 必须是由两个整数构成的数组，例如 [[0, 10]]")
    return 参数


def 执行工具(工具名: str, 参数: dict[str, Any]) -> Any:
    if 工具名 not in 工具函数:
        raise ValueError(f"不支持的工具：{工具名}")
    参数 = _转为操作参数(工具名, dict(参数))
    if 工具名 == "create_directory":
        调用参数 = {"路径": 参数["path"]}
    elif 工具名 == "write_file":
        调用参数 = {"路径": 参数["path"], "内容": 参数["content"]}
    elif 工具名 == "read_file":
        调用参数 = {"路径": 参数["path"], "编码格式": 参数.get("encoding", "utf-8")}
    elif 工具名 in ("read_file_lines", "read_file_chars"):
        调用参数 = {"路径": 参数["path"], "行范围" if 工具名.endswith("lines") else "字符范围": tuple(tuple(项) for 项 in 参数["ranges"]), "编码格式": 参数.get("encoding", "utf-8")}
    else:
        调用参数 = {"命令": 参数["command"], "命令功能": 参数["purpose"]}
    状态, 结果 = 工具函数[工具名](**调用参数)
    if 状态:
        raise RuntimeError(str(结果))
    return 结果


class DeepSeekAgent:
    def __init__(self, api_key: str | None = None, *, timeout: int = 60):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.timeout = timeout
        self.messages: list[dict[str, Any]] = [{
            "role": "system",
            "content": "你是一个谨慎的文件操作助手。只能使用提供的六个工具；缺少路径、范围、命令或命令用途时先请求用户补充，不要猜测。用户提供的相对路径以启动 agent.py 时的当前工作目录为基准，是有效路径，不要仅因它不是绝对路径而追问。",
        }]

    def _请求(self) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("未设置 DEEPSEEK_API_KEY 环境变量")
        内容 = json.dumps({"model": DEEPSEEK_MODEL, "messages": self.messages, "tools": 工具定义, "tool_choice": "auto"}).encode("utf-8")
        请求 = Request(DEEPSEEK_API_URL, data=内容, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(请求, timeout=self.timeout) as 响应:
                return json.loads(响应.read().decode("utf-8"))
        except HTTPError as 异常:
            详情 = 异常.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek API HTTP {异常.code}: {详情}") from 异常
        except URLError as 异常:
            raise RuntimeError(f"无法连接 DeepSeek API：{异常.reason}") from 异常

    def 对话(self, 用户输入: str) -> str:
        self.messages.append({"role": "user", "content": 用户输入})
        for 轮数 in range(最大对话轮数):
            _输出进度(f"正在请求 DeepSeek（第 {轮数 + 1}/{最大对话轮数} 轮）...")
            响应 = self._请求()
            消息 = 响应["choices"][0]["message"]
            工具调用 = 消息.get("tool_calls") or []
            self.messages.append(消息)
            if not 工具调用:
                _输出进度("模型已返回答复。")
                return 消息.get("content") or ""
            for 调用 in 工具调用:
                名称 = 调用["function"]["name"]
                try:
                    预览参数 = json.loads(调用["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    预览参数 = {"arguments": 调用["function"].get("arguments", "")}
                显示名称 = 工具显示名称.get(名称, 名称)
                _输出进度(f"准备执行：{显示名称}；参数：{_参数摘要(预览参数)}")
                try:
                    参数 = json.loads(调用["function"].get("arguments", "{}"))
                    _输出进度(f"等待确认：{显示名称}（请在置顶弹窗中选择“是”或“否”）...")
                    结果 = 执行工具(名称, 参数)
                    内容 = json.dumps({"成功": True, "结果": 结果}, ensure_ascii=False)
                    _输出进度(f"执行完成：{显示名称}。")
                except Exception as 异常:
                    内容 = json.dumps({"成功": False, "错误": str(异常)}, ensure_ascii=False)
                    _输出进度(f"执行失败：{显示名称}；{异常}")
                self.messages.append({"role": "tool", "tool_call_id": 调用["id"], "name": 名称, "content": 内容})
        raise RuntimeError("对话超过最大工具调用轮数")


def main() -> None:
    print(f"DeepSeek Agent ({DEEPSEEK_MODEL})，输入 exit 退出。")
    agent = DeepSeekAgent()
    while True:
        try:
            用户输入 = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if 用户输入.lower() in {"exit", "quit", "退出"}:
            break
        if not 用户输入:
            continue
        try:
            print(f"\nAgent：{agent.对话(用户输入)}")
        except Exception as 异常:
            print(f"Agent 错误：{异常}")


if __name__ == "__main__":
    main()
