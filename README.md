# Tool Calls Support Detector

检测任意 OpenAI 兼容 API 是否支持 `tool_calls`（函数调用）的桌面 GUI 工具。

## 功能特性

- **多策略测试** — 内置 4 组不同 tool 定义 + prompt 组合，全面覆盖模型的 tool_calls 能力
- **双重检测机制** — 同时检查 `message.tool_calls` 和 `finish_reason == "tool_calls"` 两种判定方式
- **批量模型测试** — 逗号分隔输入多个模型名，逐个检测并汇总结果
- **预设 API** — 一键切换 OpenAI / Kimi (Moonshot) / DeepSeek / 硅基流动
- **自定义 API** — 支持任意 OpenAI 兼容的 Base URL
- **SSL 跳过** — 默认勾选，兼容自签证书和代理环境
- **可拖拽分割面板** — 左侧结果表格 + 右侧响应详情，比例自由调整
- **暗色主题** — 基于 ttkbootstrap darkly 主题

## 内置测试策略

| 策略 | Tool 定义 | 测试 Prompt |
|------|----------|-------------|
| 算术计算 | `multiply(a, b)` | What is 19*21? |
| 天气查询 | `get_weather(city, unit)` | What's the weather like in Beijing today? |
| 联网搜索 | `web_search(query)` + `fetch_page(url)` | 请联网搜索今天的科技新闻头条。 |
| 多工具混合 | `calculate(expression)` + `lookup_stock(symbol)` | What is Tesla's current stock price? Also calculate 15% of 2400. |

选择「全部尝试」时，4 组策略逐一测试，任意一组返回 `tool_calls` 即判定为支持。

## 预设 API

| 预设 | Base URL | 默认模型 |
|------|----------|----------|
| OpenAI | `https://api.openai.com` | gpt-4o, gpt-4o-mini, gpt-3.5-turbo |
| Kimi (Moonshot) | `https://api.moonshot.cn` | kimi-k2.6, moonshot-v1-8k |
| DeepSeek | `https://api.deepseek.com` | deepseek-chat, deepseek-reasoner |
| 硅基流动 | `https://api.siliconflow.cn` | Qwen/Qwen2.5-7B-Instruct |

也可手动填写任意兼容 OpenAI 接口的 Base URL。

## 安装与运行

### 依赖

```
pip install ttkbootstrap requests
```

### 运行

**推荐（无控制台黑窗）：**

```
python tool_calls_detector.pyw
```

或双击 `tool_calls_detector.pyw` 文件。

**普通方式（会弹出控制台窗口）：**

```
python tool_calls_detector.py
```

### 系统要求

- Python 3.8+
- Windows / macOS / Linux（需有 tkinter）

## 使用方法

1. 从预设下拉框选择 API 提供商，或手动填写 Base URL
2. 填入 API Key
3. 在「模型」输入框中填写要测试的模型名（逗号分隔）
4. 点击「开始检测」
5. 左侧表格显示每个模型的检测结果，点击行可查看右侧详情

## 检测逻辑

```
发送 POST {base_url}/v1/chat/completions
  body: { model, messages, tools }

对响应 choices[0]:
  ├─ message.tool_calls 非空  →  SUPPORTED (检测方式: message.tool_calls)
  ├─ finish_reason == "tool_calls"  →  SUPPORTED (检测方式: finish_reason)
  └─ 否则  →  NOT SUPPORTED
```

## 界面预览

```
┌─────────────────────────────────────────────────────────┐
│  API 配置                                               │
│  预设: [OpenAI ▾]  Base URL: [https://api.openai.com]   │
│  API Key: [********]  模型: [gpt-4o,gpt-4o-mini]        │
│  超时: [30]  ☑ 跳过 SSL  策略: [全部尝试 ▾]             │
│  [ 开始检测 ]  [ 清空结果 ]                              │
├───────────────────────┬─────────────────────────────────┤
│  检测结果             │  响应详情                        │
│  #  模型  状态  ...   │  gpt-4o                         │
│  1  gpt-4o  PASS      │  SUPPORTED                      │
│  2  gpt-3.5 FAIL      │  RESULT SUMMARY                 │
│     ...               │    Toolsets: 算术计算,天气查询    │
│                       │  PER-TOOLSET DETAILS            │
│                       │    [1] 算术计算  PASS            │
│                       │    [2] 天气查询  PASS            │
│                       │  RAW RESPONSE JSON              │
│                       │    { "choices": [...] }         │
├───────────────────────┴─────────────────────────────────┤
│  检测完成 — 2/3 个模型支持 tool_calls           [====]  │
└─────────────────────────────────────────────────────────┘
```

## 项目结构

```
tool_calls_detector/
├── tool_calls_detector.py    # 源码（运行时会弹控制台）
├── tool_calls_detector.pyw   # 无控制台版本（推荐）
├── .gitignore
└── README.md
```

## 许可证

MIT License
