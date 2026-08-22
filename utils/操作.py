import functools
import pathlib
import subprocess
try:
	import tkinter as tk
	from tkinter import messagebox
except ImportError:
	tk = None
	messagebox = None

_TkError = tk.TclError if tk is not None else RuntimeError

def _获取同意():
	try:
		if tk is None or messagebox is None:
			raise RuntimeError("当前 Python 未安装 tkinter")
		根窗口 = tk.Tk()
		根窗口.withdraw()
		是否同意 = messagebox.askyesno("确认操作", "是否同意该操作？", parent=根窗口)
		根窗口.destroy()
		return bool(是否同意)
	except (_TkError, RuntimeError):
		答案 = ""
		while 答案 not in ("y", "n"):
			答案 = input("是否同意该操作（y/n）：").strip().lower()
		return 答案 == "y"

def _同意装饰器(操作函数):
	@functools.wraps(操作函数)
	def 执行函数(*args,**kwargs):
		if(_获取同意()):
			try:
				return (0, 操作函数(*args,**kwargs))
			except Exception as e:
				return (1, e)
		else:
			用户提示 = input("请给出提示：")
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
