# Tool Calls Support Detector

检测任意 OpenAI 兼容 API 是否支持 `tool_calls`（函数调用）的桌面 GUI 工具。

## 功能特性

- **8 组测试策略** — 覆盖单工具、多工具、强制调用、指定函数、并行调用、严格 Schema 等场景
- **双重检测机制** — 同时检查 `message.tool_calls` 和 `finish_reason == "tool_calls"` 两种判定方式
- **`tool_choice` 测试** — 支持 `auto` / `required` / 指定函数名三种模式
- **并行调用检测** — 识别模型是否支持一次返回多个 tool_calls
- **批量模型测试** — 逗号分隔输入多个模型名，逐个检测并汇总结果
- **预设 API** — 一键切换 OpenAI / Anthropic / Kimi (Moonshot) / DeepSeek / 硅基流动
- **双协议支持** — 自动识别 OpenAI 兼容接口和 Anthropic Messages API
- **自定义 API** — 支持任意 OpenAI 兼容的 Base URL
- **SSL 跳过** — 默认勾选，兼容自签证书和代理环境
- **可拖拽分割面板** — 左侧结果表格 + 右侧响应详情，比例自由调整
- **暗色主题** — 基于 ttkbootstrap darkly 主题

## 内置测试策略

| # | 策略 | Tool 定义 | Prompt | tool_choice |
|---|------|----------|--------|-------------|
| 1 | 算术计算 | `multiply(a, b)` | What is 19*21? | auto |
| 2 | 天气查询 | `get_weather(city, unit)` | What's the weather like in Beijing? | auto |
| 3 | 联网搜索 | `web_search(query)` + `fetch_page(url)` | 请联网搜索今天的科技新闻头条 | auto |
| 4 | 多工具混合 | `calculate(expr)` + `lookup_stock(sym)` | Tesla stock price + 15% of 2400 | auto |
| 5 | 强制调用 | `get_time(timezone)` | Hello! | `required` |
| 6 | 指定函数 | `greet(name)` + `farewell(name)` | The user's name is Alice. | `{type:function, function:{name:greet}}` |
| 7 | 并行调用 | `get_temperature(city)` + `get_humidity(city)` | Temperature and humidity in Beijing & Tokyo | auto |
| 8 | 严格 Schema | `create_task(title, priority, due_days)` + `strict:true` | Create a high-priority task... | auto |

选择「全部尝试」时，8 组策略逐一测试，任意一组返回 `tool_calls` 即判定为支持。

### 测试维度

- **基础能力**（策略 1-4）：模型是否能正确解析 tool 定义并生成 tool_calls
- **强制调用**（策略 5）：`tool_choice: "required"` 是否生效，即使 prompt 无关也能触发
- **指定函数**（策略 6）：`tool_choice: {"type":"function","function":{"name":"greet"}}` 是否精确调用指定函数
- **并行调用**（策略 7）：模型是否能在一次响应中返回多个 tool_calls
- **严格 Schema**（策略 8）：`strict: true` + `enum` + `additionalProperties:false` 约束是否生效

## 预设 API

| 预设 | Base URL | 默认模型 | 协议 |
|------|----------|----------|------|
| OpenAI | `https://api.openai.com` | gpt-4o, gpt-4o-mini, gpt-3.5-turbo | OpenAI |
| Anthropic | `https://api.anthropic.com` | claude-sonnet-4, claude-haiku-4 | Messages API |
| Kimi (Moonshot) | `https://api.moonshot.cn` | kimi-k2.6, moonshot-v1-8k | OpenAI |
| DeepSeek | `https://api.deepseek.com` | deepseek-chat, deepseek-reasoner | OpenAI |
| 硅基流动 | `https://api.siliconflow.cn` | Qwen/Qwen2.5-7B-Instruct | OpenAI |

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
4. 选择测试策略（推荐「全部尝试」）
5. 点击「开始检测」
6. 左侧表格显示每个模型的检测结果，点击行可查看右侧详情

## 检测逻辑

```
对每个测试策略:
  发送 POST {base_url}/v1/chat/completions
    body: { model, messages, tools [, tool_choice] }

  对响应 choices[0]:
    ├─ message.tool_calls 非空  →  SUPPORTED (检测方式: message.tool_calls)
    │   └─ 记录并行调用数 (parallel_count)
    ├─ finish_reason == "tool_calls"  →  SUPPORTED (检测方式: finish_reason)
    └─ 否则  →  该组 NOT SUPPORTED

  任意一组 SUPPORTED → 该模型 SUPPORTED
```

## 界面预览

```
┌──────────────────────────────────────────────────────────────┐
│  API 配置                                                    │
│  预设: [OpenAI ▾]   Base URL: [https://api.openai.com]       │
│  API Key: [********]   模型: [gpt-4o,gpt-4o-mini,gpt-3.5]    │
│  超时: [30]  ☑ 跳过 SSL   策略: [全部尝试 ▾]                 │
│  [ 开始检测 ]  [ 清空结果 ]                                   │
├────────────────────────────┬─────────────────────────────────┤
│  检测结果                  │  响应详情                        │
│  #  模型     状态  ...     │  gpt-4o                         │
│  1  gpt-4o   PASS          │  SUPPORTED                      │
│  2  gpt-3.5  FAIL          │  RESULT SUMMARY                 │
│      ...                   │    Toolsets: 算术计算,天气查询    │
│                            │    Parallel Calls: 2             │
│                            │  PER-TOOLSET DETAILS            │
│                            │    [1] 算术计算  PASS            │
│                            │    [2] 天气查询  PASS            │
│                            │    [7] 并行调用  PASS            │
│                            │      Parallel: 2                 │
│                            │  RAW RESPONSE JSON              │
│                            │    { "choices": [...] }         │
├────────────────────────────┴─────────────────────────────────┤
│  检测完成 — 2/3 个模型支持 tool_calls                [====]  │
└──────────────────────────────────────────────────────────────┘
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
