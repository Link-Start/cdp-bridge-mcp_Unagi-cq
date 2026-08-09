#!/usr/bin/env python3
"""V3: CDP Bridge 与 Playwright MCP 的可审计端到端测评。

V3 修正 V2 把“有非空回答”当作任务成功的问题，并增加：

- 场景级验收规则和业务错误识别；
- 本地确定性夹具与外部动态网页分层；
- 固定被测源码/Playwright MCP 版本；
- 交替执行顺序、均值/中位数、原始 JSON 结果；
- 前置条件失败与任务 0 分严格区分。

示例：
  uv run python eval_mcp_compare_v3.py --preflight --build-check
  ANTHROPIC_API_KEY=... uv run python eval_mcp_compare_v3.py --repeats 3
  ANTHROPIC_API_KEY=... uv run python eval_mcp_compare_v3.py --suite all
"""

from __future__ import annotations

import argparse
import asyncio
import compileall
import datetime as dt
import json
import os
import platform
import queue
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "eval_compare_report.md"
ARTIFACT = HERE / "eval_results.json"

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic").rstrip("/")
MODEL = os.environ.get("ANTHROPIC_MODEL", "deepseek-v4-pro")
CDP_URL = os.environ.get("CDP_BRIDGE_URL", "http://127.0.0.1:8000/mcp")
CDP_TOKEN = os.environ.get("CDP_BRIDGE_TOKEN", "")
CDP_CMD = shlex.split(os.environ.get("CDP_BRIDGE_CMD", "uv run cdp-bridge"))
PW_CMD = shlex.split(
    os.environ.get(
        "PLAYWRIGHT_MCP_CMD",
        "npx -y @playwright/mcp@0.0.79 --headless --isolated --image-responses omit",
    )
)

INIT_TIMEOUT = 30
TOOL_TIMEOUT = 45
LLM_TIMEOUT = 120
MAX_ROUNDS = 20
FORBIDDEN_ANSWER_MARKERS = (
    "无法完成",
    "无法访问",
    "访问失败",
    "未能获取",
    "no browser tabs connected",
    "tool error",
    "tool timeout",
)


@dataclass(frozen=True)
class Case:
    key: str
    query: str
    group: str
    note: str
    required_groups: tuple[tuple[str, ...], ...] = ()
    pass_ratio: float = 1.0
    scored: bool = True


CASES = (
    Case(
        "fixture_extract",
        "浏览 {fixture}/，告诉我订单编号、商品名称和应付金额。",
        "core",
        "确定性本地页面；三项事实必须全部正确。",
        (("ZX-314" ,), ("青瓷机械键盘",), ("¥899", "899 元", "899元")),
    ),
    Case(
        "fixture_interact",
        "浏览 {fixture}/interact，点击“显示验证码”按钮，然后告诉我出现的验证码。",
        "core",
        "确定性交互页面；答案必须包含点击后由接口返回的验证码。",
        (("BRIDGE-V3-7291",),),
    ),
    Case(
        "numpy",
        "浏览 https://www.runoob.com/numpy/numpy-tutorial.html，找到并概括 NumPy 位运算章节。",
        "core",
        "外部公开页面；至少命中 4/6 组关键概念。",
        (
            ("bitwise_and", "按位与"),
            ("bitwise_or", "按位或"),
            ("bitwise_xor", "按位异或"),
            ("invert", "取反"),
            ("left_shift", "左移"),
            ("right_shift", "右移"),
        ),
        pass_ratio=4 / 6,
    ),
    Case(
        "xiaohongshu",
        "打开小红书，告诉我首页第一篇内容的标题。若页面被风控或未登录，请明确说明。",
        "live",
        "真实登录态诊断；内容动态且缺少独立真值，不进入质量排名。",
        scored=False,
    ),
    Case(
        "tabs",
        "列出当前浏览器的标签页标题和 URL。",
        "diagnostic",
        "两侧会话模型不同，仅作能力诊断，不进入横向排名。",
        scored=False,
    ),
)


@dataclass
class Check:
    name: str
    status: str
    detail: str


@dataclass
class ToolRecord:
    name: str
    args: dict[str, Any]
    elapsed: float
    ok: bool
    result_chars: int
    error: str = ""
    output: str = ""


@dataclass
class Run:
    backend: str
    case: str
    repeat: int
    started_at: str
    completed: bool = False
    passed: bool | None = None
    quality: float | None = None
    api_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed: float = 0.0
    final_text: str = ""
    error: str = ""
    tools: list[ToolRecord] = field(default_factory=list)


def esc(value: Any, limit: int = 300) -> str:
    text = str(value if value is not None else "")
    text = text.replace("\n", " ").replace("|", "\\|").replace("`", "\\`")
    return text[:limit] + ("…" if len(text) > limit else "")


def command_version(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable ({exc})"
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[-1] if output else f"exit={result.returncode}"


def git_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "unknown"


class MCPClient:
    def __init__(
        self,
        name: str,
        *,
        cmd: list[str] | None = None,
        cwd: str | None = None,
        url: str | None = None,
        bearer_token: str = "",
    ):
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.url = url
        self.bearer_token = bearer_token
        self.proc: subprocess.Popen[str] | None = None
        self.tools: dict[str, dict[str, Any]] = {}
        self.session_id: str | None = None
        self._id = 0
        self._pending: dict[int, queue.Queue] = {}
        self._stderr_tail: list[str] = []
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def transport(self) -> str:
        return "http" if self.url else "stdio"

    def start(self) -> bool:
        if not self.url:
            try:
                self.proc = subprocess.Popen(
                    self.cmd or [],
                    cwd=self.cwd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
            except (OSError, FileNotFoundError) as exc:
                self._stderr_tail.append(str(exc))
                return False
            threading.Thread(target=self._read_stdout, daemon=True).start()
            threading.Thread(target=self._read_stderr, daemon=True).start()

        init = self.call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "cdp-bridge-eval-v3", "version": "3.0"},
            },
            INIT_TIMEOUT,
        )
        if init is None:
            return False
        self.notify("notifications/initialized", {})
        listed = self.call("tools/list", {}, TOOL_TIMEOUT) or {}
        self.tools = {
            item["name"]: item
            for item in listed.get("tools", [])
            if isinstance(item, dict) and item.get("name")
        }
        return bool(self.tools)

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def notify(self, method: str, params: dict[str, Any]) -> None:
        if self.url:
            self._http_request({"jsonrpc": "2.0", "method": method, "params": params}, TOOL_TIMEOUT)
        else:
            self._send_stdio({"jsonrpc": "2.0", "method": method, "params": params})

    def call(self, method: str, params: dict[str, Any], timeout: int) -> dict[str, Any] | None:
        request_id = self._next_id()
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        if self.url:
            message = self._http_request(payload, timeout)
            if not message:
                return None
            return message.get("result", {"_error": message.get("error", "JSON-RPC error")})

        result_queue: queue.Queue = queue.Queue()
        self._pending[request_id] = result_queue
        self._send_stdio(payload)
        try:
            message = result_queue.get(timeout=timeout)
            return message.get("result", {"_error": message.get("error", "JSON-RPC error")})
        except queue.Empty:
            return None
        finally:
            self._pending.pop(request_id, None)

    def _http_request(self, payload: dict[str, Any], timeout: int) -> dict[str, Any] | None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        request = urllib.request.Request(self.url or "", body, method="POST", headers=headers)
        try:
            with self._opener.open(request, timeout=timeout) as response:
                self.session_id = response.headers.get("Mcp-Session-Id", self.session_id)
                raw = response.read().decode("utf-8", "replace")
        except (OSError, urllib.error.URLError, urllib.error.HTTPError):
            return None
        for line in raw.splitlines():
            if line.startswith("data:"):
                line = line[5:].strip()
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _send_stdio(self, payload: dict[str, Any]) -> None:
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def _read_stdout(self) -> None:
        if not self.proc or not self.proc.stdout:
            return
        for line in self.proc.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            request_id = message.get("id")
            if request_id in self._pending:
                self._pending[request_id].put(message)

    def _read_stderr(self) -> None:
        if not self.proc or not self.proc.stderr:
            return
        for line in self.proc.stderr:
            self._stderr_tail.append(line.rstrip())
            del self._stderr_tail[:-30]

    def tool(self, name: str, arguments: dict[str, Any], save_output: bool) -> ToolRecord:
        if name not in self.tools:
            return ToolRecord(name, arguments, 0.0, False, 0, f"unknown tool: {name}")
        started = time.perf_counter()
        result = self.call("tools/call", {"name": name, "arguments": arguments}, TOOL_TIMEOUT)
        elapsed = time.perf_counter() - started
        text, error = tool_result_text(result)
        return ToolRecord(name, arguments, elapsed, not error, len(text), error, text if save_output else "")

    def stop(self) -> None:
        if not self.proc:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
        self.proc = None

    def stderr_summary(self) -> str:
        return " | ".join(self._stderr_tail[-3:])


def tool_result_text(result: dict[str, Any] | None) -> tuple[str, str]:
    if result is None:
        return "[tool timeout]", "tool timeout"
    if result.get("_error"):
        error = str(result["_error"])
        return f"[tool error] {error}", error[:300]
    content = result.get("content", "")
    if isinstance(content, list):
        text = "\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
    else:
        text = str(content)
    if result.get("isError"):
        return text, (text or "MCP isError=true")[:300]

    semantic_error = ""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if isinstance(payload, dict):
        status = str(payload.get("status", "")).lower()
        if status in {"error", "failed", "failure"}:
            semantic_error = str(payload.get("msg") or payload.get("error") or status)
        elif payload.get("success") is False:
            semantic_error = str(payload.get("error") or payload.get("message") or "success=false")
    return text, semantic_error[:300]


def tool_text_for_model(record: ToolRecord) -> str:
    if record.output:
        return record.output[:16000]
    if record.error:
        return f"[tool error] {record.error}"
    return f"[tool output omitted by harness; {record.result_chars} chars]"


def llm(messages: list[dict[str, Any]], tools: list[dict[str, Any]], system: str) -> dict[str, Any]:
    body = {"model": MODEL, "max_tokens": 4096, "messages": messages, "tools": tools, "system": system}
    request = urllib.request.Request(
        f"{BASE_URL}/v1/messages",
        json.dumps(body, ensure_ascii=False).encode(),
        method="POST",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=LLM_TIMEOUT) as response:
            return json.loads(response.read().decode())
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        return {"_error": str(exc)}


def tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": tool["name"],
        "description": str(tool.get("description", ""))[:2000],
        "input_schema": tool.get("inputSchema") or tool.get("input_schema") or {"type": "object"},
    }


def validate(case: Case, run: Run) -> None:
    if not run.completed:
        run.passed = False if case.scored else None
        run.quality = 0.0 if case.scored else None
        return
    if not case.scored:
        run.passed = None
        run.quality = None
        return
    lowered = run.final_text.lower()
    if any(marker in lowered for marker in FORBIDDEN_ANSWER_MARKERS):
        run.passed = False
        run.quality = 0.0
        return
    hits = sum(any(term.lower() in lowered for term in group) for group in case.required_groups)
    run.quality = round(hits / len(case.required_groups), 2) if case.required_groups else 0.0
    run.passed = run.quality >= case.pass_ratio


def run_case(
    client: MCPClient,
    case: Case,
    query: str,
    repeat: int,
    system: str,
    save_tool_output: bool,
) -> Run:
    run = Run(client.name, case.key, repeat, dt.datetime.now().astimezone().isoformat(timespec="seconds"))
    started = time.perf_counter()
    messages: list[dict[str, Any]] = [{"role": "user", "content": query}]
    schemas = [tool_schema(tool) for tool in client.tools.values()]
    for round_no in range(1, MAX_ROUNDS + 1):
        run.api_calls = round_no
        response = llm(messages, schemas, system)
        if response.get("_error"):
            run.error = str(response["_error"])
            break
        usage = response.get("usage", {})
        run.input_tokens += int(usage.get("input_tokens", 0) or 0)
        run.output_tokens += int(usage.get("output_tokens", 0) or 0)
        content = response.get("content", [])
        uses = [item for item in content if isinstance(item, dict) and item.get("type") == "tool_use"]
        texts = [str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"]
        if not uses:
            run.final_text = " ".join(texts).strip()
            run.completed = bool(run.final_text) and response.get("stop_reason") != "max_tokens"
            if not run.completed:
                run.error = "empty or truncated final answer"
            break
        messages.append({"role": "assistant", "content": content})
        tool_results = []
        for use in uses:
            record = client.tool(str(use.get("name", "")), use.get("input", {}), save_output=True)
            run.tools.append(record)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": use.get("id", ""),
                    "content": tool_text_for_model(record),
                    "is_error": not record.ok,
                }
            )
            if not save_tool_output:
                record.output = ""
        messages.append({"role": "user", "content": tool_results})
    else:
        run.error = f"exceeded {MAX_ROUNDS} LLM rounds"
    run.elapsed = time.perf_counter() - started
    validate(case, run)
    return run


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/reveal":
            self._send("application/json; charset=utf-8", b'{"code":"BRIDGE-V3-7291"}')
            return
        if self.path.startswith("/interact"):
            body = """<!doctype html><html lang='zh'><head><meta charset='utf-8'><title>V3 交互夹具</title></head>
<body><main><h1>交互验证</h1><button id='reveal'>显示验证码</button><output id='code'>尚未显示</output></main>
<script>document.querySelector('#reveal').onclick=async()=>{const r=await fetch('/reveal');const d=await r.json();document.querySelector('#code').textContent=d.code;};</script>
</body></html>""".encode()
            self._send("text/html; charset=utf-8", body)
            return
        body = """<!doctype html><html lang='zh'><head><meta charset='utf-8'><title>V3 订单夹具</title></head>
<body><main><h1>订单详情</h1><dl><dt>订单编号</dt><dd>ZX-314</dd><dt>商品</dt><dd>青瓷机械键盘</dd><dt>应付金额</dt><dd>¥899</dd></dl></main></body></html>""".encode()
        self._send("text/html; charset=utf-8", body)

    def _send(self, content_type: str, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


class FixtureServer:
    def __init__(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def __enter__(self) -> "FixtureServer":
        self.thread.start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def local_checks(build_check: bool) -> list[Check]:
    checks: list[Check] = []
    py_ok = sys.version_info >= (3, 10)
    checks.append(Check("Python 版本", "PASS" if py_ok else "FAIL", platform.python_version()))

    manifest = ROOT / "src/cdp_bridge/tmwd_cdp_bridge/manifest.json"
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    manifest_version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
    project_version = project_match.group(1) if project_match else "missing"
    same = project_version == manifest_version
    checks.append(Check("版本一致性", "PASS" if same else "FAIL", f"pyproject={project_version}; extension={manifest_version}"))

    compiled = compileall.compile_dir(str(ROOT / "src"), quiet=1)
    checks.append(Check("Python 编译", "PASS" if compiled else "FAIL", "src/cdp_bridge"))

    for command in ("uv", "npx"):
        path = shutil.which(command)
        checks.append(Check(f"命令 {command}", "PASS" if path else "FAIL", path or "not found"))

    tracked_tests = subprocess.run(
        ["git", "ls-files", "tests"], cwd=ROOT, text=True, capture_output=True, check=False
    ).stdout.splitlines()
    checks.append(
        Check(
            "仓库自动化测试",
            "PASS" if tracked_tests else "WARN",
            f"tracked test files: {len(tracked_tests)}" if tracked_tests else "未发现已跟踪的 tests 源文件",
        )
    )

    if build_check:
        try:
            result = subprocess.run(
                ["uv", "build"], cwd=ROOT, text=True, capture_output=True, timeout=180, check=False
            )
            detail_lines = (result.stdout + result.stderr).strip().splitlines()
            detail = detail_lines[-1] if detail_lines else f"exit={result.returncode}"
            checks.append(Check("包构建", "PASS" if result.returncode == 0 else "FAIL", detail))
        except (OSError, subprocess.TimeoutExpired) as exc:
            checks.append(Check("包构建", "FAIL", str(exc)))
    else:
        checks.append(Check("包构建", "SKIP", "使用 --build-check 执行"))
    return checks


def start_clients(config: argparse.Namespace, checks: list[Check]) -> tuple[dict[str, MCPClient], bool]:
    clients: dict[str, MCPClient] = {}
    cdp_browser_ready = False
    if not config.playwright_only:
        cdp = MCPClient("CDP Bridge", url=CDP_URL, bearer_token=CDP_TOKEN)
        if not cdp.start() and not config.cdp_http_only:
            cdp.stop()
            cdp = MCPClient("CDP Bridge", cmd=CDP_CMD, cwd=str(ROOT))
            cdp.start()
        if cdp.tools:
            clients[cdp.name] = cdp
            tabs_count = 0
            record = ToolRecord("browser_get_tabs", {}, 0.0, False, 0, "not called")
            # Give the extension its normal auto-reconnect window after a new stdio server starts.
            for attempt in range(6):
                record = cdp.tool("browser_get_tabs", {}, save_output=True)
                try:
                    tabs_count = len(json.loads(record.output).get("tabs", []))
                except (json.JSONDecodeError, AttributeError):
                    tabs_count = 0
                if tabs_count or cdp.transport == "http" or attempt == 5:
                    break
                time.sleep(1)
            cdp_browser_ready = record.ok and tabs_count > 0
            checks.append(
                Check(
                    "CDP Bridge MCP",
                    "PASS",
                    f"transport={cdp.transport}; tools={len(cdp.tools)}; tabs={tabs_count}",
                )
            )
            checks.append(
                Check(
                    "CDP 浏览器会话",
                    "PASS" if cdp_browser_ready else "BLOCKED",
                    f"connected tabs={tabs_count}; 请加载扩展并保持至少一个网页标签页" if not cdp_browser_ready else f"connected tabs={tabs_count}",
                )
            )
            if cdp_browser_ready:
                scan = cdp.tool("browser_scan", {"tabs_only": True}, save_output=False)
                checks.append(
                    Check(
                        "CDP 只读工具冒烟",
                        "PASS" if scan.ok else "FAIL",
                        f"browser_scan(tabs_only=true); {scan.result_chars} chars" if scan.ok else scan.error,
                    )
                )
        else:
            detail = cdp.stderr_summary() or f"HTTP={CDP_URL}; command={' '.join(CDP_CMD)}"
            checks.append(Check("CDP Bridge MCP", "BLOCKED", detail))
            cdp.stop()

    if not config.cdp_only:
        playwright = MCPClient("Playwright", cmd=PW_CMD, cwd=str(ROOT))
        if playwright.start():
            clients[playwright.name] = playwright
            checks.append(Check("Playwright MCP", "PASS", f"tools={len(playwright.tools)}; command={' '.join(PW_CMD)}"))
            tabs = playwright.tool("browser_tabs", {"action": "list"}, save_output=False)
            checks.append(
                Check(
                    "Playwright 只读工具冒烟",
                    "PASS" if tabs.ok else "FAIL",
                    f"browser_tabs(list); {tabs.result_chars} chars" if tabs.ok else tabs.error,
                )
            )
        else:
            checks.append(Check("Playwright MCP", "BLOCKED", playwright.stderr_summary() or "startup failed"))
            playwright.stop()
    return clients, cdp_browser_ready


def selected_cases(config: argparse.Namespace) -> list[Case]:
    if config.case != "all":
        return [case for case in CASES if case.key == config.case]
    if config.suite == "core":
        return [case for case in CASES if case.group == "core"]
    return list(CASES)


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def render_report(
    runs: list[Run],
    cases: list[Case],
    clients: dict[str, MCPClient],
    checks: list[Check],
    config: argparse.Namespace,
    generated_at: str,
) -> None:
    revision = git_revision()
    version = project_version()
    lines = [
        "# V3 CDP Bridge vs Playwright MCP 测试报告",
        "",
        f"**生成时间**: {generated_at}",
        f"**被测版本**: `cdp-bridge {version}` (`{revision}`)",
        f"**模型**: `{esc(MODEL)}`",
        f"**API**: `{esc(BASE_URL)}`",
        f"**Playwright MCP**: `0.0.79`",
        f"**测试模式**: `{'preflight' if config.preflight else config.suite}`；重复次数 `{config.repeats}`",
        "",
        "## 1. 执行结论",
        "",
    ]
    failed = [check for check in checks if check.status == "FAIL"]
    blocked = [check for check in checks if check.status == "BLOCKED"]
    scored_runs = [run for run in runs if run.passed is not None]
    if runs:
        passed = sum(run.passed is True for run in scored_runs)
        lines.append(f"本次执行了 **{len(runs)}** 次任务，其中可评分任务 **{passed}/{len(scored_runs)}** 通过。")
    else:
        lines.append("本次仅完成本地检查与 MCP 预检，**未执行在线 LLM 对比任务**；未执行不计为 0 分或失败样本。")
    if blocked:
        lines.append("阻塞项：" + "；".join(f"{item.name}（{item.detail}）" for item in blocked) + "。")
    if failed:
        lines.append("失败项：" + "；".join(item.name for item in failed) + "。")
    lines += [
        "",
        "## 2. V3 相对 V2 的修正",
        "",
        "- V2 将非空最终文本直接记为成功，导致 Playwright 在小红书场景明确报告访问失败仍被统计为 100% 成功；V3 改为场景级验收。",
        "- 工具调用不仅检查 JSON-RPC，还识别 `isError=true`、`status=error` 和 `success=false` 等业务错误。",
        "- 核心对比加入本地确定性读取/交互夹具；小红书和标签页场景降级为诊断项，不进入质量排名。",
        "- 默认测试当前工作区源码；Playwright MCP 固定为 `0.0.79`，避免 `latest` 漂移。",
        "- 每轮交替后端顺序，原始结构化结果写入 `eval_results.json`，便于审计和二次计算。",
        "",
        "## 3. 本地检查与前置条件",
        "",
        "| 检查项 | 状态 | 详情 |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {esc(check.name)} | **{check.status}** | {esc(check.detail, 500)} |")

    lines += ["", "## 4. MCP 工具清单", ""]
    for name, client in clients.items():
        lines += [f"### {name}（{len(client.tools)} 个工具，{client.transport}）", "", "| 工具 | 描述 |", "|---|---|"]
        for tool_name, tool in sorted(client.tools.items()):
            lines.append(f"| `{esc(tool_name, 100)}` | {esc(tool.get('description', ''), 360)} |")
        lines.append("")
    if not clients:
        lines += ["MCP 服务均未就绪。", ""]

    lines += ["## 5. 核心对比结果", ""]
    if not scored_runs:
        lines += ["未执行。需要 API Key、两个 MCP 服务，以及至少一个已连接 CDP 浏览器标签页。", ""]
    else:
        lines += [
            "| 场景 | MCP | n | 通过率 | 平均质量 | 中位耗时 | 平均工具调用 | 工具成功率 | 中位总 Token |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for case in cases:
            if not case.scored:
                continue
            for backend in ("CDP Bridge", "Playwright"):
                group = [run for run in scored_runs if run.case == case.key and run.backend == backend]
                if not group:
                    continue
                tool_calls = [tool for run in group for tool in run.tools]
                success_rate = sum(run.passed is True for run in group) / len(group)
                quality = statistics.mean(float(run.quality or 0) for run in group)
                tool_rate = sum(tool.ok for tool in tool_calls) / len(tool_calls) if tool_calls else 0.0
                tokens = [run.input_tokens + run.output_tokens for run in group]
                lines.append(
                    f"| {case.key} | {backend} | {len(group)} | {success_rate:.1%} | {quality:.2f} | "
                    f"{median([run.elapsed for run in group]):.2f}s | {statistics.mean(len(run.tools) for run in group):.1f} | "
                    f"{tool_rate:.1%} | {median(tokens):,.0f} |"
                )
        lines.append("")

    lines += ["## 6. 逐次运行明细", ""]
    if not runs:
        lines += ["未执行在线任务。", ""]
    for run in runs:
        case = next(item for item in CASES if item.key == run.case)
        verdict = "诊断项" if run.passed is None else ("通过" if run.passed else "失败")
        quality = "N/A" if run.quality is None else f"{run.quality:.2f}"
        lines += [
            f"### {run.backend} / {run.case} / 第 {run.repeat} 次",
            "",
            f"- 结论：{verdict}；完成：{'是' if run.completed else '否'}；质量：{quality}；API：{run.api_calls} 轮；Token：{run.input_tokens + run.output_tokens:,}；耗时：{run.elapsed:.2f}s",
            f"- 验收口径：{case.note}",
        ]
        if run.error:
            lines.append(f"- 错误：`{esc(run.error, 500)}`")
        lines += ["", "| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |", "|---:|---|---|---:|---|---:|---|"]
        for index, tool in enumerate(run.tools, 1):
            lines.append(
                f"| {index} | `{esc(tool.name, 100)}` | `{esc(json.dumps(tool.args, ensure_ascii=False), 260)}` | "
                f"{tool.elapsed:.2f}s | {'✓' if tool.ok else '✗'} | {tool.result_chars:,} | {esc(tool.error, 180)} |"
            )
        if not run.tools:
            lines.append("| - | *(无工具调用)* | | | | | |")
        lines += ["", "**模型最终答案**:", "", esc(run.final_text, 2400) or "*(无)*", ""]

    lines += [
        "## 7. 方法与限制",
        "",
        "- 核心夹具保证两侧访问相同内容，但 CDP Bridge 使用真实浏览器，Playwright 使用隔离浏览器；两者仍不是纯协议微基准。",
        "- NumPy 属于外部网页，可能受网络、页面改版和广告影响。小红书受登录态、推荐流和风控影响，因此只作能力诊断。",
        "- 默认不保存完整工具输出，避免把真实标签页或页面隐私写入仓库；需要审计正文时显式使用 `--save-tool-output`。",
        "- 至少运行 3 次后再比较中位数；单次结果只能作为冒烟测试。",
        "- CDP 核心测试会导航当前 MCP 活动标签页，运行前应使用专门测试标签页。",
        "",
        "## 8. 复跑命令",
        "",
        "```bash",
        "# 预检 + 本地构建",
        "uv run python reports/V-003-2026-08-09/eval_mcp_compare_v3.py --preflight --build-check",
        "",
        "# 核心对比，每个场景 3 次",
        "ANTHROPIC_API_KEY=... uv run python reports/V-003-2026-08-09/eval_mcp_compare_v3.py --repeats 3",
        "",
        "# 加上真实登录态与标签页诊断",
        "ANTHROPIC_API_KEY=... uv run python reports/V-003-2026-08-09/eval_mcp_compare_v3.py --suite all --repeats 3",
        "```",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V3 CDP Bridge vs Playwright MCP evaluation")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--suite", choices=("core", "all"), default="core")
    parser.add_argument("--case", choices=[case.key for case in CASES] + ["all"], default="all")
    parser.add_argument("--cdp-only", action="store_true")
    parser.add_argument("--playwright-only", action="store_true")
    parser.add_argument("--cdp-http-only", action="store_true", help="CDP HTTP 失败后不回退到当前工作区 stdio")
    parser.add_argument("--preflight", action="store_true", help="检查本地构建、MCP 和浏览器会话，不调用 LLM")
    parser.add_argument("--build-check", action="store_true", help="预检时执行 uv build")
    parser.add_argument("--save-tool-output", action="store_true", help="在 JSON 中保存完整工具输出（可能包含隐私）")
    parser.add_argument(
        "--system-prompt",
        default="你是严谨的浏览器测试助手。只使用提供的工具获取事实；工具或页面失败时必须明确报告，不得臆测。完成后给出简洁、可核验的答案。",
    )
    return parser.parse_args()


def main() -> int:
    config = parse_args()
    if config.repeats < 1:
        raise SystemExit("--repeats 必须 >= 1")
    if config.cdp_only and config.playwright_only:
        raise SystemExit("--cdp-only 与 --playwright-only 不能同时使用")

    generated_at = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    checks = local_checks(config.build_check)
    if API_KEY:
        checks.append(Check("LLM API Key", "PASS", "ANTHROPIC_API_KEY is set"))
    else:
        checks.append(Check("LLM API Key", "BLOCKED", "ANTHROPIC_API_KEY 未设置"))

    clients, cdp_browser_ready = start_clients(config, checks)
    cases = selected_cases(config)
    runs: list[Run] = []
    can_run = not config.preflight and bool(API_KEY) and bool(clients)
    paired = not config.cdp_only and not config.playwright_only
    if not config.preflight and paired and ("CDP Bridge" not in clients or "Playwright" not in clients or not cdp_browser_ready):
        can_run = False
        checks.append(Check("成对测评门槛", "BLOCKED", "两侧 MCP 与 CDP 浏览器会话必须同时就绪"))
    elif not config.preflight and not config.playwright_only and not cdp_browser_ready:
        can_run = False
        checks.append(Check("CDP 测评门槛", "BLOCKED", "没有已连接的浏览器标签页"))

    try:
        if can_run:
            with FixtureServer() as fixture:
                for case_index, case in enumerate(cases):
                    query = case.query.format(fixture=fixture.url)
                    for repeat in range(1, config.repeats + 1):
                        order = [client for client in clients.values()]
                        if (case_index + repeat) % 2 == 0:
                            order.reverse()
                        for client in order:
                            print(f"[{case.key}] {client.name} repeat={repeat}", file=sys.stderr, flush=True)
                            runs.append(
                                run_case(
                                    client,
                                    case,
                                    query,
                                    repeat,
                                    config.system_prompt,
                                    config.save_tool_output,
                                )
                            )
    finally:
        for client in clients.values():
            client.stop()

    artifact = {
        "schema_version": 3,
        "generated_at": generated_at,
        "revision": git_revision(),
        "cdp_bridge_version": project_version(),
        "model": MODEL,
        "base_url": BASE_URL,
        "playwright_mcp": "0.0.79",
        "config": {
            "suite": config.suite,
            "case": config.case,
            "repeats": config.repeats,
            "preflight": config.preflight,
            "save_tool_output": config.save_tool_output,
        },
        "checks": [asdict(check) for check in checks],
        "clients": {
            name: {"transport": client.transport, "tools": sorted(client.tools)} for name, client in clients.items()
        },
        "runs": [asdict(run) for run in runs],
    }
    ARTIFACT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    render_report(runs, cases, clients, checks, config, generated_at)
    print(f"报告已生成：{OUT}")
    print(f"结构化结果：{ARTIFACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
