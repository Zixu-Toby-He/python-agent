import ctypes
import functools
import json
import os
import pathlib
import subprocess
try:
	import tkinter as tk
	from tkinter import messagebox
except ImportError:
	tk = None
	messagebox = None

_TkError = tk.TclError if tk is not None else RuntimeError

def _获取同意(操作名称 = "操作", 参数 = None):
	参数摘要 = json.dumps(参数 or {}, ensure_ascii=False, indent=2, default=str)
	if len(参数摘要) > 1200:
		参数摘要 = 参数摘要[:1200] + "\n……（参数过长，已省略）"
	提示文字 = "请求执行：{}\n\n参数：\n{}\n\n是否同意该操作？".format(操作名称, 参数摘要)
	print("\n[操作确认] 正在等待弹窗确认：{}（若弹窗未在前台，请按 Alt+Tab 查看）".format(操作名称), flush=True)
	try:
		if os.name == "nt":
			弹窗标志 = 0x00000004 | 0x00000020 | 0x00010000 | 0x00040000
			选择结果 = ctypes.windll.user32.MessageBoxW(
				None,
				提示文字,
				"Agent 操作确认",
				弹窗标志,
			)
			return 选择结果 == 6
		if tk is None or messagebox is None:
			raise RuntimeError("当前 Python 未安装 tkinter")
		根窗口 = tk.Tk()
		根窗口.withdraw()
		根窗口.attributes("-topmost", True)
		根窗口.update()
		是否同意 = messagebox.askyesno("Agent 操作确认", 提示文字)
		根窗口.destroy()
		return bool(是否同意)
	except (_TkError, RuntimeError, OSError, AttributeError):
		print("\n[操作确认] 无法显示图形弹窗，已切换到命令行确认。", flush=True)
		答案 = ""
		while 答案 not in ("y", "n"):
			答案 = input(f"{提示文字}\n是否同意该操作（y/n）：").strip().lower()
		return 答案 == "y"

def _同意装饰器(操作函数):
	@functools.wraps(操作函数)
	def 执行函数(*args,**kwargs):
		if(_获取同意(操作函数.__name__, {"位置参数": args, "关键字参数": kwargs})):
			print("\n[操作确认] 已允许，开始执行：{}".format(操作函数.__name__), flush=True)
			try:
				return (0, 操作函数(*args,**kwargs))
			except Exception as e:
				return (1, e)
		else:
			print("\n[操作确认] 已拒绝：{}".format(操作函数.__name__), flush=True)
			用户提示 = input("\n请给出拒绝原因或修改提示：")
			return (1, ValueError("用户不同意操作，并给出提示：{}".format(用户提示)))
	return 执行函数

@_同意装饰器
def 新建文件夹(路径):
	pathlib.Path(路径).mkdir(exist_ok=True,parents=True)

@_同意装饰器
def 写入文件(路径, 内容):
	with pathlib.Path(路径).open("w", encoding="utf-8") as f:
		f.write(内容)

@_同意装饰器
def 读取文件(路径, 编码格式 = "utf-8"):
	with pathlib.Path(路径).open("r", encoding=编码格式) as f:
		内容 = f.read()
		字符数 = len(内容)
		行数 = len(内容.split("\n"))
		if (字符数 > 10_0000):
			raise ValueError("文件过长，需要分行或分字符阅读，该文件总计 {} 行，{} 字符".format(行数, 字符数))
		return 内容

@_同意装饰器
def 分行读取文件(路径, 行范围: tuple[tuple[int, int]], 编码格式 = "utf-8"):
	with pathlib.Path(路径).open("r", encoding = 编码格式) as f:
		内容 = f.read().split("\n")
		返回内容 = []
		for 起始行号, 终止行号 in 行范围:
			返回内容.append("\n".join(内容[起始行号:终止行号]))
		return tuple(返回内容)

@_同意装饰器
def 分字符读取文件(路径, 字符范围: tuple[tuple[int, int]], 编码格式 = "utf-8"):
	with pathlib.Path(路径).open("r", encoding = 编码格式) as f:
		内容 = f.read()
		返回内容 = []
		for 起始字符号, 终止字符号 in 字符范围:
			返回内容.append(内容[起始字符号:终止字符号])
		return tuple(返回内容)

@_同意装饰器
def 执行powershell命令(命令, 命令功能):
	结果 = subprocess.run(
		["powershell", "-NoProfile", "-NonInteractive", "-Command", 命令],
		capture_output=True,
		text=True,
		encoding="utf-8",
		errors="replace",
		check=False,
	)
	return {
		"功能": 命令功能,
		"返回码": 结果.returncode,
		"标准输出": 结果.stdout,
		"标准错误": 结果.stderr,
	}
