# V3 CDP Bridge vs Playwright MCP 测试报告

**生成时间**: 2026-08-09T23:48:28+08:00
**被测版本**: `cdp-bridge 0.1.23` (`313216d82ad3`)
**模型**: `deepseek-v4-pro`
**API**: `https://api.deepseek.com/anthropic`
**Playwright MCP**: `0.0.79`
**测试模式**: `core`；重复次数 `3`

## 1. 执行结论

本次执行了 **18** 次任务，其中可评分任务 **18/18** 通过。

## 2. V3 相对 V2 的修正

- V2 将非空最终文本直接记为成功，导致 Playwright 在小红书场景明确报告访问失败仍被统计为 100% 成功；V3 改为场景级验收。
- 工具调用不仅检查 JSON-RPC，还识别 `isError=true`、`status=error` 和 `success=false` 等业务错误。
- 核心对比加入本地确定性读取/交互夹具；小红书和标签页场景降级为诊断项，不进入质量排名。
- 默认测试当前工作区源码；Playwright MCP 固定为 `0.0.79`，避免 `latest` 漂移。
- 每轮交替后端顺序，原始结构化结果写入 `eval_results.json`，便于审计和二次计算。

## 3. 本地检查与前置条件

| 检查项 | 状态 | 详情 |
|---|---|---|
| Python 版本 | **PASS** | 3.10.20 |
| 版本一致性 | **PASS** | pyproject=0.1.23; extension=0.1.23 |
| Python 编译 | **PASS** | src/cdp_bridge |
| 命令 uv | **PASS** | /Users/unagi/.local/bin/uv |
| 命令 npx | **PASS** | /usr/local/bin/npx |
| 仓库自动化测试 | **WARN** | 未发现已跟踪的 tests 源文件 |
| 包构建 | **SKIP** | 使用 --build-check 执行 |
| LLM API Key | **PASS** | ANTHROPIC_API_KEY is set |
| CDP Bridge MCP | **PASS** | transport=stdio; tools=10; tabs=6 |
| CDP 浏览器会话 | **PASS** | connected tabs=6 |
| CDP 只读工具冒烟 | **PASS** | browser_scan(tabs_only=true); 922 chars |
| Playwright MCP | **PASS** | tools=24; command=npx -y @playwright/mcp@0.0.79 --headless --isolated --image-responses omit |
| Playwright 只读工具冒烟 | **PASS** | browser_tabs(list); 41 chars |

## 4. MCP 工具清单

### CDP Bridge（10 个工具，stdio）

| 工具 | 描述 |
|---|---|
| `browser_batch` | Run multiple extension/CDP commands in one request.      Args:         commands: Command objects supported by the extension, such as             {"cmd":"cdp","method":"DOM.getDocument","params":{"depth":1}}.         tab_id: Optional tab ID inherited by commands that omit tabId.         timeout: Seconds to wait for the batch result.      |
| `browser_execute_js` | Execute JavaScript in the browser and capture results plus DOM changes.      Args:         script: JavaScript code to execute (or JSON command for CDP operations).         switch_tab_id: Switch to this tab before executing.         no_monitor: Skip DOM change monitoring (faster, less info).      |
| `browser_focus_tab` | Bring a Chrome tab to the foreground: activate the tab AND focus its window.      Unlike browser_switch_tab (which only changes the MCP-side active session     without touching the visible Chrome UI), this actually makes the tab visible     to the user. Use this when the user can't find the tab the agent is working     on (e.g. across many windows / Spaces /… |
| `browser_get_tabs` | Get all open browser tabs with their IDs, URLs, and titles. |
| `browser_navigate` | Navigate the active tab to a URL.      Args:         url: The URL to navigate to.      |
| `browser_save_image` | Save base64 screenshot data to PNG file.      Args:         screenshot_json_str_or_file: JSON output from browser_screenshot tool, or path to a JSON file containing the screenshot data.         output_path: Output PNG file path or directory. Behavior:             - Existing directory: save as {directory}/screenshot_{timestamp}.png             - File path wit… |
| `browser_scan` | Get simplified HTML content of the active tab plus tab list. The HTML is optimized for LLM consumption (stripped of scripts, styles, invisible elements).      Args:         tabs_only: Only return tab list without page content (saves tokens).         switch_tab_id: Switch to this tab before scanning.         text_only: Return plain text instead of simplified … |
| `browser_screenshot` | Take a screenshot of the active tab (returns base64 PNG).      Args:         tab_id: Optional tab ID to screenshot. Uses active tab if empty.      |
| `browser_switch_tab` | Switch the active MCP browser tab without changing the visible Chrome tab.      Args:         tab_id: The tab ID to switch to (from browser_get_tabs).      |
| `browser_wait` | Wait until JavaScript condition returns a truthy value.      Args:         condition_js: JavaScript expression or script. The return value is tested for truthiness.         timeout: Maximum seconds to wait.         interval: Seconds between checks.         switch_tab_id: Optional tab ID to make active before waiting.      |

### Playwright（24 个工具，stdio）

| 工具 | 描述 |
|---|---|
| `browser_click` | Perform click on a web page |
| `browser_close` | Close the page |
| `browser_console_messages` | Returns all console messages |
| `browser_drag` | Perform drag and drop between two elements |
| `browser_drop` | Drop files or MIME-typed data onto an element, as if dragged from outside the page. At least one of "paths" or "data" must be provided. |
| `browser_evaluate` | Evaluate JavaScript expression on page or element |
| `browser_file_upload` | Upload one or multiple files |
| `browser_fill_form` | Fill multiple form fields |
| `browser_find` | Search the accessibility snapshot of the current page for text or a regular expression. Returns matching snapshot nodes with a few lines of surrounding context (like search snippets), each shown under its path from the root of the tree, which is cheaper than capturing the whole snapshot when you only need to locate an element and its ref. |
| `browser_handle_dialog` | Handle a dialog |
| `browser_hover` | Hover over element on page |
| `browser_navigate` | Navigate to a URL |
| `browser_navigate_back` | Go back to the previous page in the history |
| `browser_network_request` | Returns full details (headers and body) of a single network request, or a single part if \`part\` is set. Use the number from browser_network_requests. |
| `browser_network_requests` | Returns a numbered list of network requests since loading the page. Use browser_network_request with the number to get full details. |
| `browser_press_key` | Press a key on the keyboard |
| `browser_resize` | Resize the browser window |
| `browser_run_code_unsafe` | Run a Playwright code snippet. Unsafe: executes arbitrary JavaScript in the Playwright server process and is RCE-equivalent. |
| `browser_select_option` | Select an option in a dropdown |
| `browser_snapshot` | Capture accessibility snapshot of the current page, this is better than screenshot |
| `browser_tabs` | List, create, close, or select a browser tab. |
| `browser_take_screenshot` | Take a screenshot of the current page. You can't perform actions based on the screenshot, use browser_snapshot for actions. |
| `browser_type` | Type text into editable element |
| `browser_wait_for` | Wait for text to appear or disappear or a specified time to pass |

## 5. 核心对比结果

| 场景 | MCP | n | 通过率 | 平均质量 | 中位耗时 | 平均工具调用 | 工具成功率 | 中位总 Token |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| fixture_extract | CDP Bridge | 3 | 100.0% | 1.00 | 12.56s | 2.0 | 100.0% | 940 |
| fixture_extract | Playwright | 3 | 100.0% | 1.00 | 11.03s | 2.0 | 100.0% | 773 |
| fixture_interact | CDP Bridge | 3 | 100.0% | 1.00 | 16.37s | 3.0 | 100.0% | 1,084 |
| fixture_interact | Playwright | 3 | 100.0% | 1.00 | 22.54s | 5.0 | 80.0% | 1,451 |
| numpy | CDP Bridge | 3 | 100.0% | 1.00 | 37.24s | 4.7 | 100.0% | 7,212 |
| numpy | Playwright | 3 | 100.0% | 1.00 | 60.52s | 8.0 | 83.3% | 21,535 |

## 6. 逐次运行明细

### CDP Bridge / fixture_extract / 第 1 次

- 结论：通过；完成：是；质量：1.00；API：3 轮；Token：2,658；耗时：12.63s
- 验收口径：确定性本地页面；三项事实必须全部正确。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/"}` | 0.61s | ✓ | 69 |  |
| 2 | `browser_scan` | `{}` | 0.83s | ✓ | 1,019 |  |

**模型最终答案**:

根据页面内容，以下是结果：  \| 字段 \| 内容 \| \|------\|------\| \| **订单编号** \| ZX-314 \| \| **商品名称** \| 青瓷机械键盘 \| \| **应付金额** \| ¥899 \|  以上信息来源于 \`http://127.0.0.1:49591/\` 页面中 \`<dl>\` 定义列表内的数据，可直接核验。

### Playwright / fixture_extract / 第 1 次

- 结论：通过；完成：是；质量：1.00；API：3 轮；Token：5,043；耗时：11.03s
- 验收口径：确定性本地页面；三项事实必须全部正确。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/"}` | 0.10s | ✓ | 221 |  |
| 2 | `browser_snapshot` | `{}` | 0.01s | ✓ | 345 |  |

**模型最终答案**:

根据页面内容，以下是订单信息：  - **订单编号**：ZX-314 - **商品名称**：青瓷机械键盘 - **应付金额**：¥899

### Playwright / fixture_extract / 第 2 次

- 结论：通过；完成：是；质量：1.00；API：3 轮；Token：757；耗时：13.09s
- 验收口径：确定性本地页面；三项事实必须全部正确。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/"}` | 0.07s | ✓ | 221 |  |
| 2 | `browser_snapshot` | `{}` | 0.01s | ✓ | 363 |  |

**模型最终答案**:

根据页面内容，提取到的订单信息如下：  \| 字段 \| 值 \| \|------\|-----\| \| **订单编号** \| ZX-314 \| \| **商品名称** \| 青瓷机械键盘 \| \| **应付金额** \| ¥899 \|  以上信息均来自页面 http://127.0.0.1:49591/ 的"订单详情"区域，可核验。

### CDP Bridge / fixture_extract / 第 2 次

- 结论：通过；完成：是；质量：1.00；API：3 轮；Token：940；耗时：11.84s
- 验收口径：确定性本地页面；三项事实必须全部正确。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/"}` | 0.42s | ✓ | 69 |  |
| 2 | `browser_scan` | `{"text_only": true}` | 0.83s | ✓ | 946 |  |

**模型最终答案**:

根据页面内容，结果如下：  - **订单编号**：ZX-314 - **商品名称**：青瓷机械键盘 - **应付金额**：¥899

### CDP Bridge / fixture_extract / 第 3 次

- 结论：通过；完成：是；质量：1.00；API：3 轮；Token：827；耗时：12.56s
- 验收口径：确定性本地页面；三项事实必须全部正确。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/"}` | 0.42s | ✓ | 69 |  |
| 2 | `browser_scan` | `{"text_only": true}` | 0.82s | ✓ | 946 |  |

**模型最终答案**:

根据页面内容，提取到的信息如下：  \| 项目 \| 内容 \| \|------\|------\| \| **订单编号** \| ZX-314 \| \| **商品名称** \| 青瓷机械键盘 \| \| **应付金额** \| ¥899 \|

### Playwright / fixture_extract / 第 3 次

- 结论：通过；完成：是；质量：1.00；API：3 轮；Token：773；耗时：10.07s
- 验收口径：确定性本地页面；三项事实必须全部正确。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/"}` | 0.07s | ✓ | 221 |  |
| 2 | `browser_snapshot` | `{}` | 0.01s | ✓ | 363 |  |

**模型最终答案**:

根据页面内容，提取结果如下：  \| 字段 \| 值 \| \|------\|-----\| \| **订单编号** \| ZX-314 \| \| **商品名称** \| 青瓷机械键盘 \| \| **应付金额** \| ¥899 \|  以上信息均来自页面 \`http://127.0.0.1:49591/\`，标题为「V3 订单夹具」，可直接核验。

### Playwright / fixture_interact / 第 1 次

- 结论：通过；完成：是；质量：1.00；API：7 轮；Token：1,627；耗时：26.23s
- 验收口径：确定性交互页面；答案必须包含点击后由接口返回的验证码。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/interact"}` | 0.08s | ✓ | 237 |  |
| 2 | `browser_snapshot` | `{}` | 0.00s | ✓ | 216 |  |
| 3 | `browser_click` | `{"target": "ref=f3e4", "element": "显示验证码按钮"}` | 0.01s | ✗ | 94 | ### Error Error: browserBackend.callTool: Unknown engine "ref" while parsing selector ref=f3e4 |
| 4 | `browser_find` | `{"text": "显示验证码"}` | 0.01s | ✓ | 155 |  |
| 5 | `browser_run_code_unsafe` | `{"code": "async (page) => {\n  await page.getByRole('button', { name: '显示验证码' }).click();\n  // Wait a bit for the verification code to appear\n  await page.waitForTimeout(1000);\n  return await page.textContent('body');\n}"}` | 2.07s | ✓ | 457 |  |
| 6 | `browser_snapshot` | `{}` | 0.01s | ✓ | 235 |  |

**模型最终答案**:

点击"显示验证码"按钮后，出现的验证码是：  **BRIDGE-V3-7291**

### CDP Bridge / fixture_interact / 第 1 次

- 结论：通过；完成：是；质量：1.00；API：4 轮；Token：1,194；耗时：17.50s
- 验收口径：确定性交互页面；答案必须包含点击后由接口返回的验证码。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/interact"}` | 0.42s | ✓ | 77 |  |
| 2 | `browser_scan` | `{}` | 0.82s | ✓ | 1,007 |  |
| 3 | `browser_execute_js` | `{"script": "document.getElementById('reveal').click();"}` | 2.64s | ✓ | 172 |  |

**模型最终答案**:

验证码已出现：**BRIDGE-V3-7291**。  验证码显示在 \`<output id="code">\` 元素中，从"尚未显示"变为了 **BRIDGE-V3-7291**。

### CDP Bridge / fixture_interact / 第 2 次

- 结论：通过；完成：是；质量：1.00；API：4 轮；Token：1,052；耗时：16.37s
- 验收口径：确定性交互页面；答案必须包含点击后由接口返回的验证码。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/interact"}` | 0.42s | ✓ | 77 |  |
| 2 | `browser_scan` | `{}` | 0.82s | ✓ | 1,007 |  |
| 3 | `browser_execute_js` | `{"script": "document.getElementById('reveal').click();"}` | 2.64s | ✓ | 172 |  |

**模型最终答案**:

点击按钮后，验证码已出现：**BRIDGE-V3-7291**。

### Playwright / fixture_interact / 第 2 次

- 结论：通过；完成：是；质量：1.00；API：6 轮；Token：1,451；耗时：22.54s
- 验收口径：确定性交互页面；答案必须包含点击后由接口返回的验证码。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/interact"}` | 0.11s | ✓ | 237 |  |
| 2 | `browser_snapshot` | `{}` | 0.00s | ✓ | 216 |  |
| 3 | `browser_click` | `{"target": "ref=f4e4", "element": "显示验证码按钮"}` | 0.00s | ✗ | 94 | ### Error Error: browserBackend.callTool: Unknown engine "ref" while parsing selector ref=f4e4 |
| 4 | `browser_run_code_unsafe` | `{"code": "async (page) => {\n  await page.click('button:has-text(\"显示验证码\")');\n  await page.waitForTimeout(500);\n  return await page.evaluate(() => document.body.innerText);\n}"}` | 1.55s | ✓ | 250 |  |
| 5 | `browser_snapshot` | `{}` | 0.01s | ✓ | 235 |  |

**模型最终答案**:

操作完成。点击"显示验证码"按钮后，页面状态区域显示的验证码是：  **BRIDGE-V3-7291**

### Playwright / fixture_interact / 第 3 次

- 结论：通过；完成：是；质量：1.00；API：5 轮；Token：1,106；耗时：22.07s
- 验收口径：确定性交互页面；答案必须包含点击后由接口返回的验证码。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/interact"}` | 0.07s | ✓ | 237 |  |
| 2 | `browser_snapshot` | `{}` | 0.01s | ✓ | 216 |  |
| 3 | `browser_click` | `{"target": "ref=f5e4", "element": "显示验证码按钮"}` | 0.00s | ✗ | 94 | ### Error Error: browserBackend.callTool: Unknown engine "ref" while parsing selector ref=f5e4 |
| 4 | `browser_run_code_unsafe` | `{"code": "async (page) => {\n  await page.getByRole('button', { name: '显示验证码' }).click();\n  // Wait a moment for the page to update\n  await page.waitForTimeout(500);\n  return await page.evaluate(() => document.body.innerText);\n}"}` | 1.55s | ✓ | 305 |  |

**模型最终答案**:

验证码已出现：**BRIDGE-V3-7291**  这是点击"显示验证码"按钮后页面显示的内容。

### CDP Bridge / fixture_interact / 第 3 次

- 结论：通过；完成：是；质量：1.00；API：4 轮；Token：1,084；耗时：16.33s
- 验收口径：确定性交互页面；答案必须包含点击后由接口返回的验证码。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "http://127.0.0.1:49591/interact"}` | 0.42s | ✓ | 77 |  |
| 2 | `browser_scan` | `{}` | 0.82s | ✓ | 1,007 |  |
| 3 | `browser_execute_js` | `{"script": "document.getElementById('reveal').click();"}` | 2.64s | ✓ | 172 |  |

**模型最终答案**:

点击按钮后，验证码已显示出来。  验证码是：**BRIDGE-V3-7291**

### CDP Bridge / numpy / 第 1 次

- 结论：通过；完成：是；质量：1.00；API：6 轮；Token：7,212；耗时：37.24s
- 验收口径：外部公开页面；至少命中 4/6 组关键概念。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-tutorial.html"}` | 0.41s | ✓ | 94 |  |
| 2 | `browser_scan` | `{"text_only": true}` | 2.65s | ✓ | 4,815 |  |
| 3 | `browser_execute_js` | `{"script": "document.querySelector('a[href*=\"bitwise\"]') \|\| document.querySelector('a[href*=\"bit\"]') \|\| [...document.querySelectorAll('a')].find(a => a.textContent.trim() === 'NumPy 位运算');"}` | 2.71s | ✓ | 259 |  |
| 4 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-binary-operators.html"}` | 0.41s | ✓ | 102 |  |
| 5 | `browser_scan` | `{"text_only": true}` | 1.02s | ✓ | 6,531 |  |

**模型最终答案**:

## NumPy 位运算 — 章节概括  该章节位于 **https://www.runoob.com/numpy/numpy-binary-operators.html**，是菜鸟教程 NumPy 系列的第 13 章。以下是核心内容：  ---  ### 一、概述  位运算是在二进制位级别上直接操作数字的运算方式。NumPy 提供了一系列 \`bitwise_\` 开头的位运算函数，它们与 Python 原生位运算符类似，但作用于 NumPy 数组，**支持矢量化处理，性能更高**，广泛用于优化和底层数据处理。  ---  ### 二、六大位运算函数  \| 操作 \| 函数 \| 说明 \| \|------\|------\|------\| \| **按位与** \| \`numpy.bitwise_and(x1, x2)\` \| 对应位都为 1 时结果为 1 \| \| **按位或** \| \`numpy.bitwise_or(x1, x2)\` \| 对应位有一个为 1 时结果为 1 \| \| **按位异或** \| \`numpy.bitwise_xor(x1, x2)\` \| 对应位相异结果为 1，相同为 0 \| \| **按位取反** \| \`numpy.invert(x)\` \| 每个位 0→1、1→0（有符号整数取补码+1） \| \| **左移** \| \`numpy.left_shift(x1, x2)\` \| 二进制位左移指定位数，右侧补 0 \| \| **右移** \| \`numpy.right_shift(x1, x2)\` \| 二进制位右移指定位数 \|  也可直接使用 Python 原生运算符：\`&\`（与）、\`\|\`（或）、\`^\`（异或）、\`~\`（取反）、\`<<\`（左移）、\`>>\`（右移）。  ---  ### 三、关键要点  1. **\`bitwise_and\`**：例如 \`np.bitwise_and(13, 17)\` → \`1\`（\`1101 & 10001 = 00001\`）。 2. **\`bitwise_or\`**：例如 \`np.bitwise_or(13, 17)\` → \`29\`（\`1101 \| 10001 = 11101\`）。 3. **\`invert\`**：对有符号整数采用**补码表示**，\`~1 = -2\`（取反 → 符号位为 1 → 其余位取反加 1）。uint8 下 \`~13 = 242\`。 4. **\`left_shift\`**：\`np.left_shift(10, 2)\` → \`40\`（\`1010 << 2 = 101000\`）。 5. **\`right_shift\`**：\`np.right_shift(10, 1)\` → \`5\`（\`1010 >> 1 = 0101\`）。 6. 支持布尔数组：如 \`np.bitwise_and([True, False], [False, True])\` → \`[False, False]\`。

### Playwright / numpy / 第 1 次

- 结论：通过；完成：是；质量：1.00；API：8 轮；Token：10,368；耗时：46.02s
- 验收口径：外部公开页面；至少命中 4/6 组关键概念。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-tutorial.html"}` | 8.35s | ✓ | 279 |  |
| 2 | `browser_find` | `{"text": "位运算"}` | 0.02s | ✓ | 1,230 |  |
| 3 | `browser_click` | `{"target": "ref=f6e78", "element": "NumPy 位运算 链接"}` | 0.00s | ✗ | 95 | ### Error Error: browserBackend.callTool: Unknown engine "ref" while parsing selector ref=f6e78 |
| 4 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-binary-operators.html"}` | 3.12s | ✓ | 296 |  |
| 5 | `browser_snapshot` | `{}` | 0.04s | ✓ | 39,525 |  |
| 6 | `browser_snapshot` | `{"target": "ref=f17e273"}` | 0.00s | ✗ | 97 | ### Error Error: browserBackend.callTool: Unknown engine "ref" while parsing selector ref=f17e273 |
| 7 | `browser_evaluate` | `{"function": "() => {\n  const article = document.querySelector('.article-body') \|\| document.querySelector('article') \|\| document.querySelector('.main-content');\n  if (article) return article.innerText;\n  return document.body.innerText.substring(0, 8000)…` | 0.51s | ✓ | 4,570 |  |

**模型最终答案**:

现在我已获取了完整的页面内容。以下是 **NumPy 位运算** 章节的概括：  ---  ## NumPy 位运算 — 章节概括  ### 概念 位运算是在二进制数字的**位级别**上进行操作，直接操作二进制各个位。NumPy 提供了 \`bitwise_\` 系列函数，对数组元素进行逐位操作，支持**矢量化处理**，性能优于普通 Python 位运算符。  ### 六大核心函数  \| 函数 \| 用途 \| \|---\|---\| \| \`numpy.bitwise_and(x1, x2)\` \| 逐位与 — 对应位都为 1 结果才为 1 \| \| \`numpy.bitwise_or(x1, x2)\` \| 逐位或 — 对应位有一个为 1 结果即为 1 \| \| \`numpy.bitwise_xor(x1, x2)\` \| 逐位异或 — 对应位相异为 1，相同为 0 \| \| \`numpy.invert(x)\` \| 逐位取反 — 0 变 1，1 变 0（有符号整数取补码+1） \| \| \`numpy.left_shift(x1, x2)\` \| 左移 — 各元素左移指定位数，右侧补 0 \| \| \`numpy.right_shift(x1, x2)\` \| 右移 — 各元素右移指定位数，左侧补 0 \|  ### 也可使用运算符 - \`&\`（与）、\`\|\`（或）、\`^\`（异或）、\`~\`（取反）、\`<<\`（左移）、\`>>\`（右移）  ### 详细讲解 每个函数都有独立小节，配有**代码示例 + 二进制表格演算**。例如： - **bitwise_and**：\`13 (0b1101) & 17 (0b10001)\` → 结果为 \`1 (0b00001)\` - **bitwise_or**：\`13 \| 17\` → 结果为 \`29 (0b11101)\` - **invert**：对 \`uint8\` 的 13 (\`00001101\`) 取反得 242 (\`11110010\`)；对有符号整数则按补码规则计算 - **left_shift**：\`10 (00001010) << 2\` → \`40 (00101000)\` - **right_shift**：\`40 (00101000) >> 2\` → \`10 (00001010)\`  ---  **总结**：该章节系统介绍了 NumPy 中 6 个位运算函数，涵盖与/或/异或/取反/左移/右移，每个函数都配有实例代码、二进制演算表和真值表，并指出可等价使用 Python 位运算符。

### Playwright / numpy / 第 2 次

- 结论：通过；完成：是；质量：1.00；API：9 轮；Token：21,535；耗时：60.52s
- 验收口径：外部公开页面；至少命中 4/6 组关键概念。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-tutorial.html"}` | 8.94s | ✓ | 372 |  |
| 2 | `browser_snapshot` | `{}` | 0.02s | ✓ | 28,777 |  |
| 3 | `browser_click` | `{"target": "ref=f27e78", "element": "NumPy 位运算 侧边栏链接"}` | 0.00s | ✗ | 96 | ### Error Error: browserBackend.callTool: Unknown engine "ref" while parsing selector ref=f27e78 |
| 4 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-binary-operators.html"}` | 4.83s | ✓ | 296 |  |
| 5 | `browser_snapshot` | `{}` | 0.04s | ✓ | 39,525 |  |
| 6 | `browser_run_code_unsafe` | `{"code": "async (page) => { await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); return 'scrolled to bottom'; }"}` | 0.54s | ✓ | 204 |  |
| 7 | `browser_snapshot` | `{}` | 0.04s | ✓ | 39,807 |  |
| 8 | `browser_evaluate` | `{"function": "() => { const article = document.querySelector('.article, .content, article, main') \|\| document.querySelector('[class*=\"article\"]') \|\| document.querySelector('[class*=\"content\"]'); if (article) return article.innerText; return document.bo…` | 0.51s | ✓ | 4,861 |  |

**模型最终答案**:

已成功获取 **NumPy 位运算** 章节的完整内容。以下是该章节的概括：  ---  ## NumPy 位运算 — 章节概括  **页面地址：** \`https://www.runoob.com/numpy/numpy-binary-operators.html\`  ### 概述  该章节介绍了 NumPy 中的位运算（Bitwise Operations）——即在二进制数字的位级别上直接操作各个位的运算。NumPy 提供了一系列 \`bitwise_\` 开头的函数，支持对数组元素进行**逐位矢量化**操作，性能优于普通的 Python 位运算符。  ### 六大核心函数  \| 操作 \| 函数 \| 描述 \| \|------\|------\|------\| \| **按位与** \| \`numpy.bitwise_and(x1, x2)\` \| 两个对应位都为 1 时结果为 1 \| \| **按位或** \| \`numpy.bitwise_or(x1, x2)\` \| 两个对应位有一个为 1 则结果为 1 \| \| **按位异或** \| \`numpy.bitwise_xor(x1, x2)\` \| 两个对应位相异时结果为 1 \| \| **按位取反** \| \`numpy.invert(x)\` \| 0 变 1，1 变 0（对有符号整数取补码+1） \| \| **左移** \| \`numpy.left_shift(x1, x2)\` \| 二进制位左移，右侧补 0 \| \| **右移** \| \`numpy.right_shift(x1, x2)\` \| 二进制位右移，左侧补 0 \|  ### 运算符等价方式  也可以直接使用 Python 运算符：\`&\`（与）、\`\|\`（或）、\`^\`（异或）、\`~\`（取反）、\`<<\`（左移）、\`>>\`（右移）。  ### 各函数详解  1. **\`bitwise_and\`**：以 13 (\`0b1101\`) 和 17 (\`0b10001\`) 为例，位与结果为 1。章节给出了逐位演算表和 A/B/AND 真值表。  2. **\`bitwise_or\`**：同样以 13 和 17 为例，位或结果为 29。同样附有逐位演算和真值表。  3. **\`invert\`**：取反操作。对有符号整数采用**补码+1**的方式，例如 \`~1 = -2\`。对于 \`uint8\` 类型的 13（\`00001101\`），取反得 242（\`11110010\`）。章节展示了 \`binary_repr\` 函数辅助查看二进制表示。  4. **\`left_shift\`**：将 10（\`00001010\`）左移 2 位得 40（\`00101000\`）。  5. **\`right_shift\`**：将 40（\`00101000\`）右移 2 位得 10（\`00001010\`）。  ### 总结  该章节全面覆盖了 NumPy 中 6 种位运算函数，每种函数都配有代码示例、输出结果、二进制演算表格，还说明了布尔数组的位运算用法（如 \`bitwise_and\` 作用于 \`bool\` 类型数组）以及与 Python 原生运算符的对应关系。

### CDP Bridge / numpy / 第 2 次

- 结论：通过；完成：是；质量：1.00；API：3 轮；Token：4,301；耗时：18.80s
- 验收口径：外部公开页面；至少命中 4/6 组关键概念。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-tutorial.html"}` | 0.43s | ✓ | 94 |  |
| 2 | `browser_scan` | `{"text_only": true}` | 0.84s | ✓ | 6,531 |  |

**模型最终答案**:

## NumPy 位运算 — 章节概括  该章节位于 NumPy 教程中，紧接在「NumPy 数组操作」之后、「NumPy 字符串函数」之前。完整内容如下：  ---  ### 1. 概述 位运算是在二进制位级别上直接操作数字的一类运算。NumPy 提供了一系列 \`bitwise_\` 开头的函数，支持对数组元素进行逐位矢量化操作，比 Python 原生位运算符性能更高，广泛应用于底层数据处理和优化场景。  ### 2. 六大位运算函数  \| 运算 \| 函数 \| 说明 \| \|------\|------\|------\| \| 按位与 \| \`numpy.bitwise_and(x1, x2)\` \| 对应位都为1时结果为1 \| \| 按位或 \| \`numpy.bitwise_or(x1, x2)\` \| 对应位有一个为1时结果为1 \| \| 按位异或 \| \`numpy.bitwise_xor(x1, x2)\` \| 对应位相异为1，相同为0 \| \| 按位取反 \| \`numpy.invert(x)\` \| 每位取反（0变1，1变0） \| \| 左移 \| \`numpy.left_shift(x1, x2)\` \| 二进制形式左移指定位数，右侧补0 \| \| 右移 \| \`numpy.right_shift(x1, x2)\` \| 二进制形式右移指定位数 \|  ### 3. 运算符等价形式 也可直接使用 Python 位运算符：\`&\`（与）、\`\|\`（或）、\`^\`（异或）、\`~\`（取反）、\`<<\`（左移）、\`>>\`（右移）。  ### 4. 各函数详解  - **\`bitwise_and\`**：示例 \`13 & 17\` → \`0b1101 & 0b10001 = 0b00001 = 1\` - **\`bitwise_or\`**：示例 \`13 \| 17\` → \`0b1101 \| 0b10001 = 0b11101 = 29\` - **\`invert\`**：对有符号整数，取补码后 +1。如 \`~1 = -2\`；对 \`uint8\` 类型，\`~13 = 242\`（因 \`00001101\` 取反得 \`11110010\`） - **\`left_shift\`**：\`np.left_shift(10, 2) = 40\`（\`00001010\` → \`00101000\`） - **\`right_shift\`**：\`np.right_shift(10, 1) = 5\`  ### 5. 核心要点 NumPy 位运算将 Python 的标量位运算扩展到了**数组级别**，实现了**矢量化**，能高效处理大规模数据。

### CDP Bridge / numpy / 第 3 次

- 结论：通过；完成：是；质量：1.00；API：8 轮；Token：10,643；耗时：55.66s
- 验收口径：外部公开页面；至少命中 4/6 组关键概念。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-tutorial.html"}` | 0.42s | ✓ | 94 |  |
| 2 | `browser_scan` | `{"text_only": true}` | 0.82s | ✓ | 4,840 |  |
| 3 | `browser_execute_js` | `{"script": "document.querySelector('a[href*=\"bitwise\"], a[href*=\"bit\"], a[href*=\"位运算\"]')?.href \|\| Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes('位运算'))?.href"}` | 2.90s | ✓ | 190 |  |
| 4 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-binary-operators.html"}` | 0.41s | ✓ | 102 |  |
| 5 | `browser_scan` | `{"text_only": true}` | 2.04s | ✓ | 6,550 |  |
| 6 | `browser_execute_js` | `{"script": "window.scrollTo(0, document.body.scrollHeight); return \"scrolled to bottom\";"}` | 2.96s | ✓ | 2,317 |  |
| 7 | `browser_execute_js` | `{"script": "document.querySelector('.article-body')?.innerText \|\| document.querySelector('.main-content')?.innerText \|\| document.querySelector('article')?.innerText \|\| document.body.innerText"}` | 3.17s | ✓ | 4,380 |  |

**模型最终答案**:

已获取到完整的 NumPy 位运算章节内容，以下是概括：  ---  ## NumPy 位运算 — 章节概括  **来源**：\`https://www.runoob.com/numpy/numpy-binary-operators.html\`  ### 概述  位运算是在二进制位级别上直接操作数字的一类运算。NumPy 提供了一系列以 \`bitwise_\` 开头的位运算函数，可对数组元素进行逐位操作，支持**矢量化处理**，性能优于原生 Python 位运算符，广泛应用于优化和底层数据处理。  ### 六大核心函数  \| 操作 \| 函数 \| \|------\|------\| \| 按位与 (AND) \| \`numpy.bitwise_and(x1, x2)\` \| \| 按位或 (OR) \| \`numpy.bitwise_or(x1, x2)\` \| \| 按位异或 (XOR) \| \`numpy.bitwise_xor(x1, x2)\` \| \| 按位取反 (NOT) \| \`numpy.invert(x)\` \| \| 左移 \| \`numpy.left_shift(x1, x2)\` \| \| 右移 \| \`numpy.right_shift(x1, x2)\` \|  ### 各函数详解  1. **\`bitwise_and\`** — 对应位都为 1 时结果为 1，否则为 0。例如 \`13 & 17 = 1\`（\`0b1101 & 0b10001 = 0b00001\`）。  2. **\`bitwise_or\`** — 对应位只要有一个为 1 结果即为 1。例如 \`13 \| 17 = 29\`（\`0b1101 \| 0b10001 = 0b11101\`）。  3. **\`bitwise_xor\`** — 对应位相异为 1，相同为 0。  4. **\`invert\`** — 按位取反（0→1，1→0）。对于有符号整数，使用**补码**表示。例如 \`~5 = -6\`，\`np.invert([13], dtype=uint8) = [242]\`。  5. **\`left_shift\`** — 二进制位左移指定位数，右侧补 0。例如 \`10 << 2 = 40\`（\`00001010 → 00101000\`）。  6. **\`right_shift\`** — 二进制位右移指定位数，左侧补 0。例如 \`40 >> 2 = 10\`（\`00101000 → 00001010\`）。  ### 运算符等价形式  也可直接使用 Python 位运算符：\`&\`（与）、\`\|\`（或）、\`^\`（异或）、\`~\`（取反）、\`<<\`（左移）、\`>>\`（右移）。

### Playwright / numpy / 第 3 次

- 结论：通过；完成：是；质量：1.00；API：10 轮；Token：21,758；耗时：62.99s
- 验收口径：外部公开页面；至少命中 4/6 组关键概念。

| # | 工具 | 参数 | 耗时 | 状态 | 返回字符 | 错误 |
|---:|---|---|---:|---|---:|---|
| 1 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-tutorial.html"}` | 5.99s | ✓ | 279 |  |
| 2 | `browser_snapshot` | `{}` | 0.03s | ✓ | 28,786 |  |
| 3 | `browser_click` | `{"target": "ref=f49e78", "element": "NumPy 位运算 链接"}` | 0.00s | ✗ | 96 | ### Error Error: browserBackend.callTool: Unknown engine "ref" while parsing selector ref=f49e78 |
| 4 | `browser_navigate` | `{"url": "https://www.runoob.com/numpy/numpy-binary-operators.html"}` | 2.56s | ✓ | 296 |  |
| 5 | `browser_snapshot` | `{}` | 0.04s | ✓ | 39,525 |  |
| 6 | `browser_evaluate` | `{"function": "() => window.scrollTo(0, document.body.scrollHeight / 2)"}` | 0.52s | ✓ | 152 |  |
| 7 | `browser_snapshot` | `{}` | 0.04s | ✓ | 39,806 |  |
| 8 | `browser_evaluate` | `{"function": "() => window.scrollTo(0, document.body.scrollHeight)"}` | 6.02s | ✓ | 148 |  |
| 9 | `browser_evaluate` | `{"function": "() => {\n  // Get the main content\n  const content = document.querySelector('.article-body') \|\| document.querySelector('.main-content') \|\| document.querySelector('article');\n  if (content) return content.innerText;\n  // fallback: get all t…` | 0.51s | ✓ | 4,782 |  |

**模型最终答案**:

我已经获取了 NumPy 位运算章节的完整内容。以下是概括：  ---  ## NumPy 位运算 — 章节概括  **来源页面：** \`https://www.runoob.com/numpy/numpy-binary-operators.html\`  ### 一、概述  位运算是在二进制数字的**位级别**上直接操作各个位的一类运算。NumPy 的 \`bitwise_\` 系列函数允许对数组元素进行逐位操作，相比 Python 原生位运算符，NumPy 版本支持**矢量化处理**，性能更高，广泛应用于底层数据优化场景。  ---  ### 二、6 个核心函数一览  \| 操作 \| 函数 \| 说明 \| \|------\|------\|------\| \| 按位与 \| \`numpy.bitwise_and(x1, x2)\` \| 逐位执行与操作 \| \| 按位或 \| \`numpy.bitwise_or(x1, x2)\` \| 逐位执行或操作 \| \| 按位异或 \| \`numpy.bitwise_xor(x1, x2)\` \| 逐位执行异或操作 \| \| 按位取反 \| \`numpy.invert(x)\` \| 逐位取反（按位非） \| \| 左移 \| \`numpy.left_shift(x1, x2)\` \| 将元素左移指定位数 \| \| 右移 \| \`numpy.right_shift(x1, x2)\` \| 将元素右移指定位数 \|  ---  ### 三、Python 运算符对应关系  也可以直接使用 \`&\`、\`\|\`、\`^\`、\`~\`、\`<<\`、\`>>\` 运算符：  - **与（&）**：两位同时为 1 时结果为 1，否则为 0。例：\`1010 & 1100 = 1000\` - **或（\|）**：任一位为 1 时结果为 1。例：\`1010 \| 1100 = 1110\` - **异或（^）**：两位相异为 1，相同为 0。例：\`1010 ^ 1100 = 0110\` - **取反（~）**：0 变 1，1 变 0。例：\`~1010 = 0101\` - **左移（<<）**：所有位左移，右侧补 0。例：\`1010 << 2 = 101000\` - **右移（>>）**：所有位右移，左侧补 0 或符号位。例：\`1010 >> 2 = 0010\`  ---  ### 四、各函数详解  #### 4.1 \`bitwise_and\` — 按位与 - \`np.bitwise_and(13, 17)\` → 输出 \`1\`（\`0b1101 & 0b10001 = 0b00001\`） - 真值表：A=1,B=1→1；其余组合→0  #### 4.2 \`bitwise_or\` — 按位或 - \`np.bitwise_or(13, 17)\` → 输出 \`29\`（\`0b1101 \| 0b10001 = 0b11101\`） - 真值表：A=0,B=0→0；其余组合→1  #### 4.3 \`invert\` — 按位取反 - 对无符号整数（如 \`uint8\`），\`np.invert([13])\` → \`[242]\`（\`00001101\` → \`11110010\`） - 对有符号整数，计算的是**补码+1**。例如 \`~1 = -2\`（步骤：原码 \`00000001\`→取反 \`11111110\`→符号位外取反 \`10000001\`→末位加1 \`10000010\`→十进制 \`-2\`）  #### 4.4 \`left_shift\` — 左移 - \`np.left_shift(10, 2)\` → \`40\`（\`00001010\` → \`00101000\`，左移两位，右侧补 0）  #### 4.5 \`right_shift\` — 右移 - \`np.right_shift(40, 2)\` → \`10\`（\`00101000\` → \`00001010\`，右移两位，左侧补 0）  ---  **总结：** 该章节系统介绍了 NumPy 的 6 个位运算函数及其对应的 Python 运算符，配合真值表、二进制演示和代码实例，涵盖了布尔数组和整数数组两种场景下的用法。

## 7. 方法与限制

- 核心夹具保证两侧访问相同内容，但 CDP Bridge 使用真实浏览器，Playwright 使用隔离浏览器；两者仍不是纯协议微基准。
- NumPy 属于外部网页，可能受网络、页面改版和广告影响。小红书受登录态、推荐流和风控影响，因此只作能力诊断。
- 默认不保存完整工具输出，避免把真实标签页或页面隐私写入仓库；需要审计正文时显式使用 `--save-tool-output`。
- 至少运行 3 次后再比较中位数；单次结果只能作为冒烟测试。
- CDP 核心测试会导航当前 MCP 活动标签页，运行前应使用专门测试标签页。

## 8. 复跑命令

```bash
# 预检 + 本地构建
uv run python reports/V-003-2026-08-09/eval_mcp_compare_v3.py --preflight --build-check

# 核心对比，每个场景 3 次
ANTHROPIC_API_KEY=... uv run python reports/V-003-2026-08-09/eval_mcp_compare_v3.py --repeats 3

# 加上真实登录态与标签页诊断
ANTHROPIC_API_KEY=... uv run python reports/V-003-2026-08-09/eval_mcp_compare_v3.py --suite all --repeats 3
```
