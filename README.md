# 轻量级 DeepSeek Agent

`agent.py` 是一个只开放 `utils/操作.py` 中六种能力的 LLM Agent：新建文件夹、写入文件、读取文件、按行读取、按字符读取和执行 PowerShell 命令。API 地址固定为 `https://api.deepseek.com/chat/completions`，模型固定为 `deepseek-v4-flash`。

## 使用

需要 Python 3.10 或更高版本。先设置 API 密钥（不要把密钥写入代码或提交到仓库）：

```powershell
$env:DEEPSEEK_API_KEY = "你的 DeepSeek API 密钥"
python agent.py
```

Agent 通过标准库发送请求，不需要安装第三方包。Windows 上每个真实操作都会由 `utils/操作.py` 使用强制置顶的系统弹窗展示操作名称和参数并请求用户同意；命令行同时实时显示 API 请求、准备执行、等待确认、确认结果、完成或失败等进度。当模型缺少路径、范围、命令或命令用途时，Agent 会弹窗询问。无法创建图形窗口时会自动退回终端输入。相对路径以启动 `agent.py` 时的当前工作目录为基准。

行范围和字符范围使用 Python 切片语义，格式例如 `[[0, 10], [20, 30]]`，终止位置不包含在结果中。
