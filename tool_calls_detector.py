"""
OpenAI Tool Calls Support Detector
检测 OpenAI 兼容 API 是否支持 tool_calls
支持多种测试策略：不同 tool 定义 + prompt 组合，finish_reason 检测
"""

import json
import threading
import time
import tkinter as tk
from tkinter import scrolledtext

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    HAS_BOOTSTRAP = True
except ImportError:
    HAS_BOOTSTRAP = False

import requests

# ── 多组测试工具定义 ──────────────────────────────────────────────────

TOOLSET_ARITHMETIC = {
    "name": "算术计算",
    "tools": [{
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two integers and return the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First operand"},
                    "b": {"type": "integer", "description": "Second operand"}
                },
                "required": ["a", "b"]
            }
        }
    }],
    "prompt": "What is 19*21?",
}

TOOLSET_WEATHER = {
    "name": "天气查询",
    "tools": [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a given city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. Beijing"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Temperature unit"}
                },
                "required": ["city"]
            }
        }
    }],
    "prompt": "What's the weather like in Beijing today?",
}

TOOLSET_SEARCH = {
    "name": "联网搜索",
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the internet for up-to-date information. Use when the user asks about recent events or facts you don't know.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_page",
                "description": "Fetch and read the content of a web page by URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to fetch"}
                    },
                    "required": ["url"]
                }
            }
        }
    ],
    "prompt": "请联网搜索今天的科技新闻头条。",
}

TOOLSET_MULTI = {
    "name": "多工具混合",
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform a math calculation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Math expression like '2+3*4'"}
                    },
                    "required": ["expression"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "lookup_stock",
                "description": "Look up the current stock price for a given ticker symbol.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock ticker, e.g. AAPL, TSLA"}
                    },
                    "required": ["symbol"]
                }
            }
        }
    ],
    "prompt": "What is Tesla's current stock price? Also calculate 15% of 2400.",
}

# tool_choice=required 强制模型必须调用工具
TOOLSET_FORCED = {
    "name": "强制调用",
    "tools": [{
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current server time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "Timezone like UTC, Asia/Shanghai"}
                },
                "required": ["timezone"]
            }
        }
    }],
    "prompt": "Hello!",
    "tool_choice": "required",
}

# tool_choice 指定具体函数
TOOLSET_FORCED_NAME = {
    "name": "指定函数",
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "greet",
                "description": "Greet a user by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "User name"}
                    },
                    "required": ["name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "farewell",
                "description": "Say goodbye to a user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "User name"}
                    },
                    "required": ["name"]
                }
            }
        }
    ],
    "prompt": "The user's name is Alice.",
    "tool_choice": {"type": "function", "function": {"name": "greet"}},
}

# 并行调用：prompt 需要同时用两个工具
TOOLSET_PARALLEL = {
    "name": "并行调用",
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_temperature",
                "description": "Get temperature for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"}
                    },
                    "required": ["city"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_humidity",
                "description": "Get humidity for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"}
                    },
                    "required": ["city"]
                }
            }
        }
    ],
    "prompt": "Tell me the temperature and humidity in both Beijing and Tokyo.",
}

# strict schema：带 enum、description 等精细约束
TOOLSET_STRICT = {
    "name": "严格 Schema",
    "tools": [{
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task with priority and category.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "description": "Task priority"},
                    "due_days": {"type": "integer", "description": "Days from now until due", "minimum": 0}
                },
                "required": ["title", "priority", "due_days"],
                "additionalProperties": False
            }
        }
    }],
    "prompt": "Create a high-priority task to review the API documentation, due in 3 days.",
}

ALL_TOOLSETS = [TOOLSET_ARITHMETIC, TOOLSET_WEATHER, TOOLSET_SEARCH, TOOLSET_MULTI,
                TOOLSET_FORCED, TOOLSET_FORCED_NAME, TOOLSET_PARALLEL, TOOLSET_STRICT]

# ── 预设 API ─────────────────────────────────────────────────────────

PRESETS = {
    "OpenAI": {"url": "https://api.openai.com", "models": "gpt-4o,gpt-4o-mini,gpt-3.5-turbo"},
    "Kimi (Moonshot)": {"url": "https://api.moonshot.cn", "models": "kimi-k2.6,moonshot-v1-8k"},
    "DeepSeek": {"url": "https://api.deepseek.com", "models": "deepseek-chat,deepseek-reasoner"},
    "硅基流动 SiliconFlow": {"url": "https://api.siliconflow.cn", "models": "Qwen/Qwen2.5-7B-Instruct"},
}


# ── 核心检测逻辑 ────────────────────────────────────────────────────

def _build_url(base_url: str) -> str:
    b = base_url.rstrip("/")
    if b.endswith("/v1"):
        return b + "/chat/completions"
    return b + "/v1/chat/completions"


def check_single(base_url, api_key, model, tools, prompt, timeout=30,
                 verify_ssl=True, tool_choice=None):
    """发送一次带 tools 的请求，返回解析后的结果 dict"""
    url = _build_url(base_url)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": tools,
    }
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    result = {
        "model": model,
        "supported": False,
        "detection_method": None,
        "tool_calls": None,
        "function_name": None,
        "arguments": None,
        "finish_reason": None,
        "raw_response": None,
        "error": None,
        "latency": None,
        "status_code": None,
        "parallel_count": 0,
        "tool_choice_used": tool_choice,
    }

    try:
        import urllib3
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        t0 = time.time()
        resp = requests.post(url, json=payload, headers=headers,
                             timeout=timeout, verify=verify_ssl)
        result["latency"] = round(time.time() - t0, 2)
        result["status_code"] = resp.status_code

        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:500]}"
            return result

        data = resp.json()
        result["raw_response"] = data

        choices = data.get("choices", [])
        if not choices:
            result["error"] = "响应中无 choices"
            return result

        choice = choices[0]
        msg = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "")
        result["finish_reason"] = finish_reason
        tool_calls = msg.get("tool_calls")

        # 策略 1: message.tool_calls 非空
        if tool_calls and len(tool_calls) > 0:
            result["supported"] = True
            result["detection_method"] = "message.tool_calls"
            result["tool_calls"] = tool_calls
            result["parallel_count"] = len(tool_calls)
            first = tool_calls[0]
            func = first.get("function", {})
            result["function_name"] = func.get("name")
            result["arguments"] = func.get("arguments")
            if len(tool_calls) > 1:
                result["function_name"] += f" (+{len(tool_calls)-1})"
            return result

        # 策略 2: finish_reason == "tool_calls"
        if finish_reason == "tool_calls":
            result["supported"] = True
            result["detection_method"] = "finish_reason=tool_calls"
            result["error"] = "finish_reason=tool_calls 但 message.tool_calls 为空（异常）"
            return result

        # 不支持
        content = msg.get("content", "")
        result["error"] = "响应中无 tool_calls"
        if content:
            result["error"] += f"\n模型文本回复: {content[:300]}"

    except requests.exceptions.Timeout:
        result["error"] = f"请求超时 ({timeout}s)"
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"连接失败: {e}"
    except json.JSONDecodeError:
        result["error"] = f"响应非 JSON: {resp.text[:300]}"
    except Exception as e:
        result["error"] = f"未知错误: {e}"

    return result


def check_model(base_url, api_key, model, timeout=30, verify_ssl=True,
                toolsets=None):
    """
    对单个模型执行全部 toolset 测试，返回汇总结果。
    """
    if toolsets is None:
        toolsets = ALL_TOOLSETS

    sub_results = []
    for ts in toolsets:
        r = check_single(base_url, api_key, model,
                         ts["tools"], ts["prompt"],
                         timeout=timeout, verify_ssl=verify_ssl,
                         tool_choice=ts.get("tool_choice"))
        r["toolset_name"] = ts["name"]
        sub_results.append(r)

    supported = any(r["supported"] for r in sub_results)

    # 汇总：取第一个成功的结果作为主结果，附带全部子结果
    first_ok = next((r for r in sub_results if r["supported"]), None)
    if first_ok:
        main = dict(first_ok)
    else:
        main = {
            "model": model, "supported": False, "detection_method": None,
            "tool_calls": None, "function_name": None, "arguments": None,
            "finish_reason": None, "raw_response": None, "latency": None,
            "status_code": None,
            "error": "\n".join(f"[{r['toolset_name']}] {r['error']}" for r in sub_results if r.get("error")),
        }

    main["supported"] = supported
    main["all_results"] = sub_results
    # toolset_name 汇总显示
    passed = [r["toolset_name"] for r in sub_results if r["supported"]]
    failed = [r["toolset_name"] for r in sub_results if not r["supported"]]
    if passed:
        main["toolset_name"] = ",".join(passed) + (" +" + str(len(failed)) + "失败" if failed else "")
    else:
        main["toolset_name"] = "全部失败"
    return main


# ── GUI ─────────────────────────────────────────────────────────────

FONT_LABEL   = ("Microsoft YaHei UI", 11)
FONT_ENTRY   = ("Microsoft YaHei UI", 11)
FONT_BTN     = ("Microsoft YaHei UI", 11, "bold")
FONT_TREE_H  = ("Microsoft YaHei UI", 11, "bold")
FONT_TREE_R  = ("Microsoft YaHei UI", 11)
FONT_DETAIL  = ("Consolas", 12)
FONT_SUMMARY = ("Microsoft YaHei UI", 11)
FONT_SECTION = ("Microsoft YaHei UI", 11, "bold")

L, X_, EW, W, E = (W, X, EW, W, E)  # 缩写


def _ins(widget, text, tag=None):
    widget.insert(END, text, tag or ())

def _kv(widget, key, value):
    _ins(widget, f"    {key}:", "key")
    _ins(widget, f"  {value}\n", "val")


class ToolCallsDetectorApp:
    def __init__(self):
        if HAS_BOOTSTRAP:
            self.root = ttk.Window(
                title="Tool Calls Support Detector",
                themename="darkly",
                size=(1320, 920),
                resizable=(True, True),
            )
        else:
            self.root = tk.Tk()
            self.root.title("Tool Calls Support Detector")
            self.root.geometry("1320x920")
            self.root.configure(bg="#2b2b2b")

        self.root.minsize(1000, 720)
        self._style_treeview()
        self._build_ui()
        self._running = False

    def _style_treeview(self):
        style = ttk.Style()
        style.configure("Treeview", font=FONT_TREE_R, rowheight=34)
        style.configure("Treeview.Heading", font=FONT_TREE_H)
        # 让 LabelFrame 标题字体也统一
        style.configure("TLabelframe.Label", font=FONT_SECTION)

    def _build_ui(self):
        OUTER_PAD = 16
        ROW_PAD   = 10

        # ━━━━━━━ 顶部: API 配置 ━━━━━━━
        cfg_outer = ttk.LabelFrame(self.root, text="  API 配置  ")
        cfg_outer.pack(fill=X, padx=OUTER_PAD, pady=(14, 6))
        cfg = ttk.Frame(cfg_outer, padding=(18, 12))
        cfg.pack(fill=X)

        # Row 0 ─ 预设 / Base URL / API Key
        r = 0
        ttk.Label(cfg, text="预设:", font=FONT_LABEL).grid(
            row=r, column=0, sticky=E, padx=(0, 6), pady=2)
        self.var_preset = tk.StringVar(value="OpenAI")
        cb_preset = ttk.Combobox(cfg, textvariable=self.var_preset, font=FONT_ENTRY,
                                 values=list(PRESETS.keys()), width=20, state="readonly")
        cb_preset.grid(row=r, column=1, sticky=EW, padx=(0, 16), pady=2)
        cb_preset.bind("<<ComboboxSelected>>", self._on_preset)

        ttk.Label(cfg, text="Base URL:", font=FONT_LABEL).grid(
            row=r, column=2, sticky=E, padx=(0, 6), pady=2)
        self.var_url = tk.StringVar(value="https://api.openai.com")
        ttk.Entry(cfg, textvariable=self.var_url, font=FONT_ENTRY).grid(
            row=r, column=3, columnspan=2, sticky=EW, padx=(0, 16), pady=2)

        ttk.Label(cfg, text="API Key:", font=FONT_LABEL).grid(
            row=r, column=5, sticky=E, padx=(0, 6), pady=2)
        key_frame = ttk.Frame(cfg)
        key_frame.grid(row=r, column=6, sticky=EW, pady=2)
        self.var_key = tk.StringVar()
        e_key = ttk.Entry(key_frame, textvariable=self.var_key, font=FONT_ENTRY, show="*")
        e_key.pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        self.var_show_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(key_frame, text="显示", variable=self.var_show_key, style="Toolbutton",
                        command=lambda: e_key.configure(show="" if self.var_show_key.get() else "*")
                        ).pack(side=LEFT)

        # Row 1 ─ 模型 / 超时 / SSL / 策略
        r = 1
        ttk.Label(cfg, text="模型 (逗号分隔):", font=FONT_LABEL).grid(
            row=r, column=0, sticky=E, padx=(0, 6), pady=(ROW_PAD, 2))
        self.var_models = tk.StringVar(value="gpt-4o,gpt-4o-mini,gpt-3.5-turbo")
        ttk.Entry(cfg, textvariable=self.var_models, font=FONT_ENTRY).grid(
            row=r, column=1, sticky=EW, padx=(0, 16), pady=(ROW_PAD, 2))

        ttk.Label(cfg, text="超时 (秒):", font=FONT_LABEL).grid(
            row=r, column=2, sticky=E, padx=(0, 6), pady=(ROW_PAD, 2))
        self.var_timeout = tk.StringVar(value="30")
        ttk.Entry(cfg, textvariable=self.var_timeout, font=FONT_ENTRY, width=8).grid(
            row=r, column=3, sticky=W, padx=(0, 16), pady=(ROW_PAD, 2))

        self.var_skip_ssl = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg, text="跳过 SSL 验证", variable=self.var_skip_ssl,
                        bootstyle="danger").grid(
            row=r, column=4, sticky=W, padx=(0, 16), pady=(ROW_PAD, 2))

        ttk.Label(cfg, text="测试策略:", font=FONT_LABEL).grid(
            row=r, column=5, sticky=E, padx=(0, 6), pady=(ROW_PAD, 2))
        self.var_strategy = tk.StringVar(value="全部尝试 (推荐)")
        ttk.Combobox(cfg, textvariable=self.var_strategy, font=FONT_ENTRY, width=18, state="readonly",
                     values=["全部尝试 (推荐)"] + [ts["name"] for ts in ALL_TOOLSETS]
                     ).grid(row=r, column=6, sticky=EW, pady=(ROW_PAD, 2))

        # Row 2 ─ 按钮
        r = 2
        btn_frame = ttk.Frame(cfg)
        btn_frame.grid(row=r, column=0, columnspan=7, sticky=W, pady=(14, 0))
        self.btn_check = ttk.Button(btn_frame, text="  开始检测  ", bootstyle="success",
                                    command=self._on_check)
        self.btn_check.pack(side=LEFT, ipady=5)
        ttk.Button(btn_frame, text="  清空结果  ", bootstyle="secondary",
                   command=self._clear_all).pack(side=LEFT, padx=(14, 0), ipady=5)

        # 列权重: 1(预设) 3(URL) 1(超时) 1(SSL) 1(策略) 3(值)
        cfg.columnconfigure(1, weight=1)
        cfg.columnconfigure(3, weight=2)
        cfg.columnconfigure(6, weight=2)

        # ━━━━━━━ 中部: 表格 + 详情 (PanedWindow 可拖拽分割) ━━━━━━━
        paned = ttk.Panedwindow(self.root, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=OUTER_PAD, pady=(6, 4))

        # ─ 左侧: 检测结果 ─
        left = ttk.LabelFrame(paned, text="  检测结果  ")
        paned.add(left, weight=3)
        left_in = ttk.Frame(left, padding=(8, 6))
        left_in.pack(fill=BOTH, expand=True)

        cols = ("idx", "model", "status", "method", "function", "args", "latency", "toolset")
        self.tree = ttk.Treeview(left_in, columns=cols, show="headings", height=12,
                                 selectmode="browse")
        col_cfg = [
            ("idx",     "#",       40, CENTER),
            ("model",   "模型",   150, W),
            ("status",  "状态",    70, CENTER),
            ("method",  "检测方式",130, W),
            ("function","函数名", 110, W),
            ("args",    "参数",   180, W),
            ("latency", "耗时",    60, CENTER),
            ("toolset", "测试组", 130, W),
        ]
        for cid, text, w, anchor in col_cfg:
            self.tree.heading(cid, text=text, anchor=anchor)
            self.tree.column(cid, width=w, minwidth=36, anchor=anchor, stretch=(cid in ("model", "args", "toolset")))
        # 滚动条
        tree_sb = ttk.Scrollbar(left_in, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_sb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        tree_sb.pack(side=RIGHT, fill=Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        # 样式
        self.tree.tag_configure("oddrow",   background="#2a2a2a")
        self.tree.tag_configure("evenrow",  background="#222222")
        self.tree.tag_configure("pass_badge", foreground="#1b5e20", background="#a5d6a7",
                                font=("Microsoft YaHei UI", 10, "bold"))
        self.tree.tag_configure("fail_badge", foreground="#b71c1c", background="#ef9a9a",
                                font=("Microsoft YaHei UI", 10, "bold"))
        self.tree.tag_configure("pass_text", foreground="#66bb6a")
        self.tree.tag_configure("fail_text", foreground="#ef5350")

        # ─ 右侧: 响应详情 ─
        right = ttk.LabelFrame(paned, text="  响应详情  ")
        paned.add(right, weight=2)
        right_in = ttk.Frame(right, padding=(8, 6))
        right_in.pack(fill=BOTH, expand=True)

        self.detail_text = scrolledtext.ScrolledText(
            right_in, wrap=WORD, font=FONT_DETAIL,
            bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4",
            relief=FLAT, state=DISABLED, padx=12, pady=10, spacing3=2)
        self.detail_text.pack(fill=BOTH, expand=True)

        # ━━━━━━━ 底部: 状态栏 ━━━━━━━
        bar = ttk.Frame(self.root, padding=(OUTER_PAD, 6, OUTER_PAD, 14))
        bar.pack(fill=X)
        self.var_summary = tk.StringVar(value="就绪 — 选择预设或输入配置后点击「开始检测」")
        ttk.Label(bar, textvariable=self.var_summary, font=FONT_SUMMARY).pack(side=LEFT)
        self.progress = ttk.Progressbar(bar, mode="determinate", length=260,
                                        bootstyle="success-striped")
        self.progress.pack(side=RIGHT, padx=(14, 0))

        self._init_detail_tags()
        self._results = []

    # ── 事件 ──

    def _on_preset(self, _=None):
        name = self.var_preset.get()
        p = PRESETS.get(name)
        if p:
            self.var_url.set(p["url"])
            self.var_models.set(p["models"])

    def _get_selected_toolsets(self):
        s = self.var_strategy.get()
        if s.startswith("全部"):
            return ALL_TOOLSETS
        for ts in ALL_TOOLSETS:
            if ts["name"] == s:
                return [ts]
        return ALL_TOOLSETS

    def _on_check(self):
        if self._running:
            return
        url = self.var_url.get().strip()
        key = self.var_key.get().strip()
        models_raw = self.var_models.get().strip()
        if not url or not models_raw:
            self._set_summary("请填写 Base URL 和模型名称")
            return
        models = [m.strip() for m in models_raw.split(",") if m.strip()]
        if not models:
            self._set_summary("模型列表为空")
            return
        try:
            timeout = int(self.var_timeout.get())
        except ValueError:
            timeout = 30

        self._clear_all()
        self._running = True
        self.btn_check.configure(state=DISABLED)
        self.progress["maximum"] = len(models)
        self.progress["value"] = 0
        self._set_summary(f"正在检测 {len(models)} 个模型...")

        verify_ssl = not self.var_skip_ssl.get()
        toolsets = self._get_selected_toolsets()
        threading.Thread(target=self._run_checks,
                         args=(url, key, models, timeout, verify_ssl, toolsets),
                         daemon=True).start()

    def _run_checks(self, url, key, models, timeout, verify_ssl, toolsets):
        for i, model in enumerate(models):
            self.root.after(0, self._set_summary, f"正在检测: {model} ({i+1}/{len(models)})...")
            result = check_model(url, key, model, timeout, verify_ssl, toolsets)
            self._results.append(result)
            self.root.after(0, self._add_result_row, result, i)

        ok = sum(1 for r in self._results if r["supported"])
        total = len(self._results)
        self.root.after(0, self._set_summary, f"检测完成 — {ok}/{total} 个模型支持 tool_calls")
        self.root.after(0, self._finish)

    def _init_detail_tags(self):
        """初始化详情面板的文字颜色标签"""
        t = self.detail_text
        t.tag_configure("title",    font=("Microsoft YaHei UI", 13, "bold"), foreground="#e0e0e0")
        t.tag_configure("pass",     foreground="#4caf50", font=("Microsoft YaHei UI", 11, "bold"))
        t.tag_configure("fail",     foreground="#f44336", font=("Microsoft YaHei UI", 11, "bold"))
        t.tag_configure("key",      foreground="#90caf9", font=("Consolas", 12))
        t.tag_configure("val",      foreground="#e0e0e0", font=("Consolas", 12))
        t.tag_configure("section",  foreground="#ffcc80", font=("Microsoft YaHei UI", 11, "bold"))
        t.tag_configure("sep",      foreground="#555555")
        t.tag_configure("error",    foreground="#ef9a9a")
        t.tag_configure("json_hdr", foreground="#80cbc4", font=("Consolas", 11, "bold"))
        t.tag_configure("json",     foreground="#b0bec5", font=("Consolas", 11))
        t.tag_configure("dim",      foreground="#888888")

    def _add_result_row(self, result, idx):
        ok = result["supported"]
        status = "PASS" if ok else "FAIL"
        method = result.get("detection_method", "-") or "-"
        func = result.get("function_name", "-") or "-"
        args_raw = result.get("arguments", "-") or "-"
        args_display = (args_raw[:28] + "...") if isinstance(args_raw, str) and len(args_raw) > 31 else str(args_raw)
        latency = str(result.get("latency", "-")) if result.get("latency") else "-"
        toolset = result.get("toolset_name", "-") or "-"

        row_bg = "oddrow" if idx % 2 == 0 else "evenrow"
        badge = "pass_badge" if ok else "fail_badge"
        text_tag = "pass_text" if ok else "fail_text"
        self.tree.insert("", END, iid=str(idx),
                         values=(idx + 1, result["model"], status, method, func, args_display, latency, toolset),
                         tags=(row_bg, badge, text_tag))
        self.progress["value"] = idx + 1

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(self._results):
            self._show_detail(self._results[idx])

    def _show_detail(self, r):
        t = self.detail_text
        t.configure(state=NORMAL)
        t.delete("1.0", END)

        ok = r["supported"]

        # ── 标题 ──
        _ins(t, f"  {r['model']}\n", "title")
        _ins(t, f"  {'SUPPORTED' if ok else 'NOT SUPPORTED'}\n\n", "pass" if ok else "fail")

        # ── 概览 ──
        _ins(t, "  RESULT SUMMARY\n", "section")
        _ins(t, "  " + "─" * 44 + "\n", "sep")
        _kv(t, "Toolsets", r.get("toolset_name", "-"))
        if r.get("detection_method"):
            _kv(t, "Detection", r["detection_method"])
        if r.get("finish_reason"):
            _kv(t, "finish_reason", r["finish_reason"])
        if r.get("function_name"):
            _kv(t, "Function", r["function_name"])
        if r.get("arguments"):
            _kv(t, "Arguments", r["arguments"])
        if r.get("latency"):
            _kv(t, "Latency", f"{r['latency']}s")
        pc = r.get("parallel_count", 0)
        if pc > 1:
            _kv(t, "Parallel Calls", str(pc))
        tc = r.get("tool_choice_used")
        if tc is not None:
            _kv(t, "tool_choice", json.dumps(tc, ensure_ascii=False) if isinstance(tc, dict) else str(tc))
        _ins(t, "\n")

        # ── 各组详情 ──
        all_results = r.get("all_results")
        if all_results:
            _ins(t, "  PER-TOOLSET DETAILS\n", "section")
            _ins(t, "  " + "─" * 44 + "\n", "sep")
            for i, sr in enumerate(all_results, 1):
                sok = sr["supported"]
                badge = " PASS " if sok else " FAIL "
                _ins(t, f"  [{i}] {sr['toolset_name']}", "key")
                _ins(t, f"  {badge}\n\n", "pass" if sok else "fail")
                if sok:
                    _kv(t, "  Method", sr.get("detection_method", "-"))
                    _kv(t, "  Function", sr.get("function_name", "-"))
                    _kv(t, "  Args", sr.get("arguments", "-"))
                    _kv(t, "  finish_reason", sr.get("finish_reason", "-"))
                    pc = sr.get("parallel_count", 0)
                    if pc > 1:
                        _kv(t, "  Parallel", str(pc))
                else:
                    err = sr.get("error", "-")
                    _ins(t, f"    Error: ", "key")
                    _ins(t, f"{err}\n\n", "error")
                if sr.get("latency"):
                    _kv(t, "  Latency", f"{sr['latency']}s")
                tc = sr.get("tool_choice_used")
                if tc is not None:
                    tc_str = json.dumps(tc, ensure_ascii=False) if isinstance(tc, dict) else str(tc)
                    _kv(t, "  tool_choice", tc_str)
                _ins(t, "\n")

        # ── 错误汇总（仅全部失败时） ──
        if not ok and r.get("error"):
            _ins(t, "  ERRORS\n", "section")
            _ins(t, "  " + "─" * 44 + "\n", "sep")
            _ins(t, f"  {r['error']}\n\n", "error")

        # ── 原始 JSON ──
        _ins(t, "  RAW RESPONSE JSON\n", "json_hdr")
        _ins(t, "  " + "─" * 44 + "\n", "sep")
        raw = r.get("raw_response")
        if raw:
            _ins(t, json.dumps(raw, indent=2, ensure_ascii=False) + "\n", "json")
        else:
            _ins(t, "  (无)\n", "dim")

        t.configure(state=DISABLED)

    def _clear_all(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._results.clear()
        self.detail_text.configure(state=NORMAL)
        self.detail_text.delete("1.0", END)
        self.detail_text.configure(state=DISABLED)

    def _set_summary(self, text):
        self.var_summary.set(text)

    def _finish(self):
        self._running = False
        self.btn_check.configure(state=NORMAL)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ToolCallsDetectorApp()
    app.run()
