import functools
import json
import pathlib
import subprocess

try:
	import tkinter
except ImportError:
	tkinter = None

_TkError = tkinter.TclError if tkinter is not None else RuntimeError

def _获取同意(操作名称 = "操作", 参数 = None):
	参数摘要 = json.dumps(参数 or {}, ensure_ascii=False, indent=2, default=str)
	if len(参数摘要) > 1200:
		参数摘要 = 参数摘要[:1200] + "\n...（参数过长，已省略）"
	提示文字 = "请求执行：{}\n\n参数：\n{}".format(操作名称, 参数摘要)
	print("\n[操作确认] 正在等待弹窗确认：{}（若弹窗未在前台，请按 Alt+Tab 查看）".format(操作名称), flush=True)
	窗口 = None
	try:
		if (tkinter is None):
			raise RuntimeError("当前 Python 未安装 tkinter")
		窗口 = tkinter.Tk()
		窗口.title("Agent 操作确认")
		窗口.geometry("620x460")
		窗口.minsize(520, 380)
		窗口.attributes("-topmost", True)

		内容框 = tkinter.Frame(窗口, padx=16, pady=14)
		内容框.pack(fill="both", expand=True)
		tkinter.Label(内容框, text="Agent 请求执行以下操作：", anchor="w", font=("Microsoft YaHei UI", 10, "bold")).pack(fill="x")
		详情框 = tkinter.Text(内容框, height=10, wrap="word")
		详情框.insert("1.0", 提示文字)
		详情框.configure(state="disabled")
		详情框.pack(fill="both", expand=True, pady=(8, 12))

		选择变量 = tkinter.StringVar(value="同意")
		tkinter.Label(内容框, text="请选择：", anchor="w").pack(fill="x")
		同意选项框 = tkinter.Frame(内容框)
		同意选项框.pack(fill="x", padx=(12, 0), pady=(4, 0))

		不同意选项框 = tkinter.Frame(内容框)
		不同意选项框.pack(fill="x", padx=(12, 0), pady=(2, 0))
		引导内容框 = tkinter.Frame(不同意选项框)
		引导框 = tkinter.Text(引导内容框, height=5, wrap="word", state="disabled")

		def 切换引导状态():
			新状态 = "normal" if 选择变量.get() == "不同意" else "disabled"
			引导框.configure(state=新状态)
			if 新状态 == "normal":
				引导框.focus_set()

		tkinter.Radiobutton(同意选项框,   text="同意",   variable=选择变量, value="同意",   command=切换引导状态).pack(anchor="w")
		tkinter.Radiobutton(不同意选项框, text="不同意", variable=选择变量, value="不同意", command=切换引导状态).pack(anchor="w")
		引导内容框.pack(fill="x", padx=(28, 0), pady=(2, 0))
		tkinter.Label(引导内容框, text="用户引导信息（可多行输入）：", anchor="w").pack(fill="x", pady=(0, 4))
		引导框.pack(fill="x")

		结果 = {"同意": False, "引导": ""}

		def 提交():
			结果["同意"] = 选择变量.get() == "同意"
			if not 结果["同意"]:
				结果["引导"] = 引导框.get("1.0", "end-1c").strip()
			窗口.destroy()

		def 关闭():
			结果["同意"] = False
			结果["引导"] = "用户关闭了确认窗口"
			窗口.destroy()

		按钮框 = tkinter.Frame(内容框)
		按钮框.pack(fill="x", pady=(12, 0))
		tkinter.Button(按钮框, text="提交", command=提交, width=12).pack(side="right")
		窗口.protocol("WM_DELETE_WINDOW", 关闭)
		窗口.bind("<Escape>", lambda _event: 关闭())
		窗口.update_idletasks()
		窗口宽度 = 窗口.winfo_width()
		窗口高度 = 窗口.winfo_height()
		横坐标 = max(0, (窗口.winfo_screenwidth() - 窗口宽度) // 2)
		纵坐标 = max(0, (窗口.winfo_screenheight() - 窗口高度) // 2)
		窗口.geometry("{}x{}+{}+{}".format(窗口宽度, 窗口高度, 横坐标, 纵坐标))
		窗口.deiconify()
		窗口.lift()
		窗口.focus_force()
		窗口.grab_set()
		窗口.after(150, lambda: (窗口.lift(), 窗口.focus_force()))
		print("\n[操作确认] 弹窗已显示，请在窗口中选择并提交。", flush=True)
		窗口.mainloop()
		return 结果["同意"], 结果["引导"]
	except (_TkError, RuntimeError, OSError, AttributeError) as 异常:
		if 窗口 is not None:
			try:
				窗口.destroy()
			except Exception:
				pass
		print("\n[操作确认] 无法显示图形弹窗：{}；已切换到命令行确认。".format(异常), flush=True)
		答案 = ""
		while 答案 not in ("y", "n"):
			答案 = input(f"{提示文字}\n是否同意该操作（y/n）：").strip().lower()
		if 答案 == "y":
			return True, ""
		print("请输入用户引导信息，输入单独一行 END 结束：")
		引导行 = []
		while True:
			行 = input()
			if 行 == "END":
				break
			引导行.append(行)
		return False, "\n".join(引导行)

def _同意装饰器(操作函数):
	@functools.wraps(操作函数)
	def 执行函数(*args,**kwargs):
		是否同意, 用户引导 = _获取同意(操作函数.__name__, {"位置参数": args, "关键字参数": kwargs})
		if 是否同意:
			print("\n[操作确认] 已允许，开始执行：{}".format(操作函数.__name__), flush=True)
			try:
				return (0, 操作函数(*args,**kwargs))
			except Exception as e:
				return (1, e)
		else:
			print("\n[操作确认] 已拒绝：{}".format(操作函数.__name__), flush=True)
			return (1, ValueError("用户不同意操作，并给出提示：{}".format(用户引导 or "（用户未填写引导信息）")))
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

def _弹窗测试():
	测试同意, 测试引导 = _获取同意(
		"确认弹窗自测",
		{"说明": "这是弹窗显示测试，不会执行文件或命令操作。"},
	)
	print("\n弹窗自测结果：同意={}，用户引导={!r}".format(测试同意, 测试引导))

if __name__ == "__main__":
	_弹窗测试()