# Progress · AI 桌面宠物

依据 `handbook.txt` 实现，Python + PySide6。

## 当前文件结构

```
mypet/
├── handbook.txt          # 纲领性文件（只读依据）
├── progress.md           # 本文件
├── chat_dialog_style_guide.txt  # 对话框外观改造的规格说明（执行摘要 + 详细要求 + 验收标准）
├── .gitignore            # 排除 __pycache__ / _test_log.txt / venv 等
├── requirements.txt      # 依赖：PySide6 / PyYAML / openai
├── start.bat             # 启动脚本（切到脚本目录，跑 main.py，出错暂停）
├── main.py               # 程序入口
├── config.yaml           # 行为与模型连接配置（含 api 段：base_url/api_key/model）
├── system_prompt.txt     # 人格 prompt（用户自定义，程序不附加任何人格倾向）
├── assets/               # GIF 素材（用户提供）
│   ├── idle/stand.gif        # idle
│   ├── walk/walk-left.gif    # 向左走（水平分量向左时播放）
│   ├── walk/walk-right.gif   # 向右走（水平分量向右时播放）
│   ├── walk/get lost.gif     # 走丢（每次走完后按概率播放一次）
│   ├── click/click.gif       # click
│   ├── drag/drag.gif         # drag
│   └── random/              # 「随机动作」的 GIF（决策选中时原地从首帧完整播一遍）
│       ├── pillow talk.gif
│       ├── sleepy.gif
│       ├── dance.gif
│       ├── look around.gif
│       ├── groom myself.gif
│       └── wind flow.gif
└── src/
    ├── __init__.py
    ├── config.py         # 加载 config.yaml，解析相对动画路径与 system_prompt 路径为绝对路径
    ├── ai_chat.py        # OpenAI 兼容流式请求线程（QThread + delta/completed/failed 信号，abort 中断）
    ├── chat_dialog.py    # 对话框：右键「开始对话」唤起，白底紫边圆角自绘窗体，AI 流式对话，关闭即中断请求并清空记忆
    └── pet_window.py     # 主窗口：无边框、透明、置顶；状态机 + 走动/点击/拖动 + 右键菜单 + 对话
```

## 每个文件干什么

| 文件 | 职责 |
|---|---|
| `main.py` | 创建 QApplication，加载配置，显示 PetWindow |
| `start.bat` | 双击启动：切到脚本目录、UTF-8 代码页、运行 main.py，失败时暂停窗口便于看报错 |
| `config.py` | 读取 `config.yaml`，把 animation 里的相对路径（含列表型 `random_actions`）与 `system_prompt` 路径拼成绝对路径；`load_system_prompt(cfg)` 读人格文件全文（缺失返回空串） |
| `src/ai_chat.py` | `ChatStreamWorker(QThread)`：后台迭代 OpenAI 兼容接口 stream，`delta`/`completed`/`failed` 三信号（主线程经自动队列连接收）；`abort()` 置中断标志并关闭底层流，中断后不再发任何信号；模块级 `_live_workers` 强引用池防「QThread destroyed while running」，线程结束自 `deleteLater`；model 未配置直接发 failed |
| `src/pet_window.py` | 桌宠窗口：Frameless + WA_TranslucentBackground + WindowStaysOnTopHint + Tool；状态机 idle/walk/random/click/drag/lost/talk/error；QMovie 播 GIF；自主行为循环：待机随机时长（`idle_duration_min/max`，待机固定播 stand.gif）→ 按 `walk_chance`/`random_chance`/`continue_idle_chance` 三项概率加权决策「走动 / 随机动画 / 继续待机」→ 执行动作 → 回待机重新计时；走动 360° 随机、碰边按轴反向、按水平分量切左右走 GIF；随机动作从 `random_actions` 挑一个原地从首帧完整播一遍（不位移，末帧检测，`random_max_ms` 可截断）；左键单击完整播 click、按住移动播 drag（跟手拖动），用户操作打断当前动作；走完按概率播 get lost.gif；右键弹原生 QMenu 菜单（`contextMenuEvent` 非对话时先 `_enter_idle()` 回待机并停计时 → `_build_context_menu()` 返回 菜单+动作→回调 映射 → `_exec_menu()` 弹出并按映射分发 → 关闭后恢复计时；对话中右键不打断 talk）；对话管理：`_on_chat_requested` 开对话框（期间 `chat_open` 为真，自主行为被拦住保持原地待机），`_on_chat_closed` 恢复计时；AI 接线：`speaking_changed(True)` 播 talk GIF（素材缺失保持待机）、`(False)` 回待机，`ai_failed` 关对话框并播一次 error GIF（素材缺失直接回待机），关框时若在 TALK 态强制回待机；对话期间拖桌宠时对话框同步跟随，点击/拖动不切 CLICK/DRAG 动画（始终 stand.gif）；对话框永久停靠角色上/下侧（`DIALOG_GAP=8`、`_dialog_side`、`_dialog_dx`），拖动时由「被拖方请求位置 + 停靠侧」经 `_drag_pair`/`_place_pair` 推出双方位置（`_dialog_anchor`/`_pet_anchor`）、顶到上/下边框翻面（`_should_flip`）、组合外框整体平移钳入屏内（`_pair_shift`），是唯一的落位入口；`_clamp_to_screen` 按外框钳单个窗口（无对话框时的回退路径） |
| `src/chat_dialog.py` | 对话框 `ChatDialog`：QPlainTextEdit 只读日志 + QLineEdit 输入 + 发送按钮；`_history` 仅存本次会话；小叉（objectName `closeButton`）是唯一关闭路径（Esc 快捷键与失活「点外部即关」均已移除，点形象/点外部都不再关闭）；日志区只按行显示用户提问与 AI 回复，不加「你：/我：」称谓前缀；AI 流式对话：发送即 `ChatStreamWorker` 后台请求（system_prompt + history），delta 缓冲后按 `STREAM_FLUSH_MS=50ms` 固定频率刷进日志区（不做每 token 重绘），完成写回 `_history`；输出中输入框与发送键禁用（`_set_input_enabled`），`_send` 也有 `_worker` 非空双保险；`closeEvent` 调 `worker.abort()` 立即中断请求；失败发 `ai_failed(str)` 由桌宠关框播 error；`speaking_changed(bool)` 上报流式中状态给桌宠播 talk；外观按 `chat_dialog_style_guide.txt`：无系统装饰（Frameless + WA_TranslucentBackground），外层（窗体本身）margin=20 留阴影空间，内层 `QWidget#inner` QSS 白底 `#FFFFFF` + 2px 紫边 `#8A2BE2` + 圆角 12 + QGraphicsDropShadowEffect 阴影；顶部行只放右上角小叉、无标题文字，整条兼拖动区（eventFilter 按 header 区分）；日志区 NoFrame + 透明背景，内容直接写在白底上；构造函数接收 `input_placeholder`（来自 `chat_dialog.input_placeholder` 配置）、`api`（连接配置）、`system_prompt`（人格全文） |
| `config.yaml` | 窗口尺寸、启动位置、各状态 GIF 路径、走动速度/时长、待机随机时长、三项行为决策概率、click/lost/random/error 截断上限、lost 触发概率、`api`（base_url/api_key/model/timeout_s）、`system_prompt`（人格文件路径）、`chat_dialog.input_placeholder` |

## 已实现的功能

- [x] 项目目录结构与配置文件骨架
- [x] 无边框、透明背景、始终置顶、不在任务栏显示的窗口
- [x] idle GIF 循环播放（stand.gif）
- [x] 启动落位：默认右下角，可配置居中
- [x] 左键按住拖拽换位（拖动中播放 drag.gif，按下点跟手不跳变）
- [x] 配置文件驱动窗口尺寸与动画路径（相对路径自动解析）
- [x] 依赖环境：Python 3.13 + PySide6 6.12 + PyYAML 6.0 + openai 3.3
- [x] 走动状态机：随机 360° 方向走动（可斜向/上下），小数累加防取整卡住
- [x] 碰屏幕四边按对应轴反转速度分量并钳制位置（碰左右翻 vx、碰上下翻 vy）
- [x] 走动 GIF 按水平分量选择：`vx < 0` 播 `walk-left.gif`，否则 `walk-right.gif`，反向瞬间自动切换
- [x] 自主行为循环（待机→决策→执行→回待机）：待机随机时长（`idle_duration_min`~`idle_duration_max`，可配）到点后，在「走动 / 随机动画 / 继续待机」三项间按 `walk_chance`/`random_chance`/`continue_idle_chance` 加权随机决策（三项按和归一化，和为 1 时即精确概率；全 0 则一直待机）；动作播完回待机重新随机计时
- [x] 随机动作（random 状态）：决策选中时从 `animation.random_actions` 列表挑一个 GIF，原地从首帧完整播一遍（不位移）后回待机（与 click/lost 同用 frameChanged 末帧检测；`random_max_ms: 0` 不截断，可配正值兜底）；无素材时退回继续待机
- [x] 左键单击完整播放 click.gif 一次后回待机（末帧检测结束；`click_max_ms: 0` 不截断，可配正值截断）
- [x] 用户操作打断：点击/拖动打断当前动作（走动 / 随机动画 / 待机计时），播对应动画，操作结束后回待机重新计时
- [x] `set_walk_enabled()` 开关走动（已由右键菜单「暂停/恢复走动」调用）
- [x] 走丢效果：每次走动结束后按概率（`lost_chance`，默认 0.3）播放 `walk/get lost.gif` 一次后回待机；支持 `lost_max_ms` 截断上限
- [x] 移除待机随机混播（原 `idle_random_chance`）：待机固定播 `stand.gif`，`random/` 目录 GIF（`animation.random_actions` 列表）只作为决策后的「随机动作」出现，职责单一
- [x] 修复 `config.py` 对空动画路径（`talk:`/`error:` 留空为 None）的崩溃
- [x] 修复素材目录重组导致的启动空白：`stand.gif` 迁至 `assets/idle/`，`config.yaml` 路径同步更新；`talk`/`error` 改为留空
- [x] 右键菜单（最小版，原生 `QMenu`）：开始对话（占位，`_on_chat_requested` 空实现）/ 暂停走动↔恢复走动（按 `walk_enabled` 动态文案，调 `set_walk_enabled`）/ 回到屏幕中央（`_place("center")`）/ 打开配置文件（`os.startfile(CONFIG_PATH)`）/ 退出（`QApplication.quit`）；菜单与「动作→回调」映射由 `_build_context_menu()` 统一构建，`contextMenuEvent` exec 后查映射分发，未选中（None）不动作
- [x] 右键即回待机：`contextMenuEvent` 一进来就 `_enter_idle()`（打断走动/随机动画/点击并播 stand.gif），再停掉待机计时使菜单期间保持静止，菜单关闭后恢复自主行为计时
- [x] 随机动画素材扩充：`animation.random_actions` 增至 6 项（新增 dance / look around / groom myself / wind flow）；行为参数调优：待机 10~40s→5~20s、`walk_chance` 0.5→0.6、`continue_idle_chance` 0.2→0.1、单次走动 3~8s→4~8s
- [x] 对话框（AI 未接入的最小版，`src/chat_dialog.py`）：右键菜单「开始对话」唤起，桌宠正上方落位（放不下落下方、按外框钳制屏内）；只读日志 + 输入框 + 发送（Enter/按钮均可）多轮输入骨架，`_history` 仅存本次会话；关闭方式 X / Esc / 点外部（窗口失活即关），`closeEvent` 清空记忆并 emit `closed`，`WA_DeleteOnClose` 销毁实例（下次打开为全新对象）；重复唤起只 raise 已开窗口
- [x] 对话期间原地待机：开框时 `_enter_idle()` 回播 stand.gif 并停待机计时，`chat_open` 拦住 `_schedule_next_behavior`/`_decide_action`（期间左键点完 click 也不恢复计时）；关框后 `_on_chat_closed` 恢复自主行为计时
- [x] 对话框外观自绘（依 `chat_dialog_style_guide.txt`）：去系统装饰（Frameless + 透明），白底紫边圆角 + 阴影，右上角紫色「×」小叉（hover 变深紫，点击走原 close() 流程），标题区可拖动窗口；视觉参数集中为模块常量（背景/边框色宽/圆角/阴影/外层 margin/小叉），无第三方 UI 库；原有关闭逻辑、信号、记忆清空、落位、raise 全部不变
- [x] 修复关对话框闪退：关闭对话框（小叉 / 点形象失活）曾连带退出整个程序——桌宠是 `Qt.Tool` 不计入「最后一个可见窗口」，对话框是唯一普通窗口，关掉即触发 QApplication 默认 `quitOnLastWindowClosed`；`main.py` 已设 `app.setQuitOnLastWindowClosed(False)`，程序只由菜单「退出」结束；关框后 `_on_chat_closed` 正常恢复待机-动作循环
- [x] 对话期间联动拖动：拖桌宠时对话框跟随、拖对话框标题区时桌宠跟随（`ChatDialog.drag_moved(QPoint)` 信号），二者相对位置保持不变（最初各自 `move` 同步位移，后由下方「拖动不重叠+翻面」改为整体落位裁决）
- [x] 修复拖动时对话框消失：对话框「点外部即关」由 WindowDeactivate 触发，桌宠是 Tool 窗口、一点击就抢激活，按下瞬间就被当成「点外部」而关闭；给桌宠加 `WindowDoesNotAcceptFocus`（Windows 下即 WS_EX_NOACTIVATE），点击/拖动桌宠不再抢激活，对话框保持打开并联动跟随；点其他应用/桌面仍失活关闭，×/Esc 不变。代价：对话框开着时点桌宠不再关闭对话框（原先点形象即关）
- [x] 对话期间形象始终待机动画：`chat_open` 时点击不进 CLICK、拖动不进 DRAG（始终 stand.gif）；关框后恢复原有 click/drag 表现
- [x] 拖动不出屏：新增 `_clamp_to_screen(widget, pos)` 按外框把窗口钳制在主屏 `availableGeometry` 内；拖桌宠（`mouseMoveEvent`）、对话框跟随位移、拖对话框带桌宠三条路径统一钳制，屏内拖动仍完全跟手、贴边即停；`_place_dialog` 也改为复用该钳制（后由下方「拖动不重叠+翻面」改为按整体外框钳制）
- [x] 拖动不重叠 + 边框翻面：对话框改为永久停靠角色上/下侧（新常量 `DIALOG_GAP=8`、`DIALOG_ABOVE/BELOW`，成员 `_dialog_side` 记停靠侧、`_dialog_dx` 记水平相对偏移，`_place_dialog` 落位时一并记录）；拖动时不再「各自位移」，而是由「被拖方的请求位置 + 停靠侧」经 `_drag_pair` → `_place_pair`（唯一落位入口）推出双方位置：`_dialog_anchor`（桌宠→对话框）/`_dialog` 对应 `_pet_anchor`（对话框→桌宠）反推，`_pair_box` 求组合外框，`_should_flip` 判定对话框被顶到上/下边框（`DIALOG_ABOVE` 且 `box.top()<screen.top()`、`DIALOG_BELOW` 且 `box.bottom()>screen.bottom()`，栈高超过屏高则不翻）则翻到另一侧（每次落位至多翻一次），最后 `_pair_shift` 把组合外框整体平移钳入主屏可用区；翻面/钳制改写落位后，`mouseMoveEvent`（桌宠侧）与 `ChatDialog.eventFilter`（对话框侧）都必须按当前实际位置重算 `_drag_offset`，否则下一次 move 仍按旧偏移把窗口拽回、翻面来回抖；`_place("center")` 落位后也经 `_drag_pair` 重新停靠，保证菜单「回到屏幕中央」不压住对话框；无对话框时回退 `_clamp_to_screen` 单窗口钳制。临时脚本 `test_pair.py` 实测：4 条路径（拖角色/拖对话框 × 上/下边框）全扫掠（含越界目标）下两窗口始终 ⊆ `availableGeometry()` 且互不相交、翻面后不抖、反向拖恢复跟手、关框后跟手与贴边行为不变
- [x] 对话框默认高度减半：`chat_dialog.py` 的 `DIALOG_HEIGHT` 420 → 210（宽度 360 不变），`setMinimumSize` 同步由 (320, 320) 降为 (320, 160)——最小尺寸必须 ≤ 默认值，否则 `resize(360, 210)` 会被最小高度顶回 320；尺寸仍是模块常量集中定义；停靠/翻面/整体钳制逻辑全用动态高度计算，无硬编码 420，改完 `test_pair.py` 全量回归通过（顺带收益：栈高 240+8+210=458 < 屏高 912，「回到屏幕中央」时桌宠能精确居中不再被整体平移让位）
- [x] 对话框外观细化（去标题 / 日志去框 / 提示文案可配置）：删除顶部「对话」标题 QLabel（窗口 `setWindowTitle("对话")` 保留），header 只留右上角小叉并继续兼作拖动区（`test_dialog_ui.py` 实测拖动不受影响）；日志区 `QPlainTextEdit` 去掉默认边框与阴影（`setFrameShape(NoFrame)` + QSS `background: transparent; border: none`），对话内容直接落在紫白对话框内部，不再另起一层「框」；输入框提示「输入消息，Enter 发送」改为可配置：`config.yaml` 新增 `chat_dialog.input_placeholder`，`ChatDialog(input_placeholder)` 构造参数传入，留空或整个 `chat_dialog` 段缺失时回退模块常量 `DEFAULT_INPUT_PLACEHOLDER`（三种情况均有断言覆盖）
- [x] AI 接入（OpenAI 兼容接口，流式）：`config.yaml` 新增 `api` 段（`base_url`/`api_key`/`model`/`timeout_s`，云端/本地改配置即切、代码零改动）与 `system_prompt`（人格文件路径，程序不附加任何人格倾向）；新增 `system_prompt.txt` 人格文件；新增 `src/ai_chat.py` 的 `ChatStreamWorker(QThread)` 后台流式请求（`delta`/`completed`/`failed` 信号，`abort()` 中断后不再发信号）；对话框发送即请求，增量按 50ms 固定频率刷进日志区（不做每 token 重绘），完成把 assistant 回复写回 `_history` 支持多轮上下文；输出中输入框/发送键禁用、完成后恢复；输出中关闭对话框（×/Esc/点外部）立即 `abort()` 中断请求；API 失败发 `ai_failed` → 桌宠关对话框并播一次 error GIF（素材缺失直接回待机，配 `error_max_ms` 截断）；`model` 未配置直接报错不发请求；离屏 mock OpenAI SSE 服务实测：流式全量文本、401 走 failed、model 缺失报配置错、abort 后不发 completed/failed 共 8 项 + 对话框/桌宠接线 11 项（禁用输入、talk 态切换、流式写日志、上下文、失败关框播 error、关闭中断回待机）全通过
- [x] talk 状态：AI 流式输出期间桌宠循环播 talk GIF（`speaking_changed(True)` 触发，素材缺失保持待机动画），输出结束回待机；对话中右键不再打断 talk；关框时若在 TALK 态强制回待机
- [x] 日志去称谓前缀：删除用户行「你：」与 AI 行「我：」，用户提问与 AI 回复各占一行直接显示（AI 回复先 `appendPlainText("")` 另起一行再流式插入）
- [x] 关闭路径收窄为仅小叉：移除 Esc 快捷键与 `event()` 里 WindowDeactivate 的「点外部即关」，点形象、点外部、按 Esc 均不再关闭对话框，只有右上角「×」可关（`closeEvent` 的清记忆/中断/emit closed 逻辑不变；注意这偏离了 handbook 第四章「X、Esc、点外部均视为关闭」，以用户 2026-10-15 的明确要求为准）
- [x] 对话框置顶：`ChatDialog` 补上 `WindowStaysOnTopHint`（桌宠窗口有、对话框此前漏加），修复桌宠在最上层但对话框被其他窗口遮挡的问题

## 已知问题 / TODO

- [ ] `talk`、`error` GIF 未制作，配置暂留空（代码已接入：有素材即播，缺失自动回退待机），待素材就绪后在 `config.yaml` 填路径
- [ ] 气泡（QPainter 自绘圆角矩形+尾巴、自动换行、流式刷新）未实现；AI 回复暂呈现于对话框日志区
- [ ] 气泡样式配置项缺失：圆角、边框色、填充色、透明度、字体、字号、最大宽度

## 版本控制（Git）

- 2026-10-12：`git init`（main 分支）初始化本仓库，新增 `.gitignore`（排除 `__pycache__/`、`*.pyc`、`_test_log.txt`、`venv/`、`.pytest_cache/`、`.ruff_cache/`）
- 2026-10-12：首次提交 `feat: 桌宠项目初始版本`，内容为代码 + 配置 + handbook + progress.md + 8 个 GIF 素材（约 11MB，纳入版本控制）
- 2026-10-12：打标签 `v1.0.0` 标记当前稳定版本
- 2026-10-12：添加远端 `origin` → `https://github.com/Iloveazusa008/my-tiny-desktop-pet.git`，`git push -u origin main --tags` 推送至 GitHub（账号 `Iloveazusa008`）
- 2026-10-12：提交 `2d214c2 docs(progress): 记录 git 初始化与 sslverify=false 踩坑原因` 并推送
- 2026-10-12：提交 `600e6da feat: 重构自主行为循环，新增随机动作状态`（4 文件，+121/−69），打标签 `v2.0.0`（备注：修改了动作循环逻辑），推送 `main` 与标签至 GitHub
- 2026-10-12：提交 `feat: 添加右键菜单与对话框`（新增 `src/chat_dialog.py`、4 个 random GIF、右键菜单与对话期间挂起自主行为、参数调优），打标签 `v2.1.0`（备注：添加右键菜单和对话框），推送 `main` 与标签至 GitHub
- 2026-10-12：提交 `feat: 完善对话框`（自绘白底紫边圆角+阴影+小叉、桌宠对话框联动拖动与停靠翻面、关框闪退与抢激活修复、提示文案可配置、新增 `chat_dialog_style_guide.txt`），打标签 `v2.2.0`（备注：对话框已完善），推送 `main` 与标签至 GitHub
- 2026-10-15：提交 `feat: 接入 AI 对话并修改窗口`（新增 `src/ai_chat.py` 流式线程与 `system_prompt.txt` 人格、`api` 配置段、talk/error 状态接线、关闭方式收窄为仅小叉、对话框置顶、handbook 同步），打标签 `v2.3.0`（备注：接入ai对话加修改窗口），推送 `main` 与标签至 GitHub

日常提交流程：`git add .` → `git commit -m "描述"` → `git push`；确认某个版本不错时可用 `git tag v1.x.x` 再 `git push --tags`。

## 备注 / 踩坑记录

- QThread 被对话框持为子对象且对话框 `WA_DeleteOnClose`：关框时线程可能还在跑，会崩「QThread: Destroyed while thread is still running」；`ChatStreamWorker` 不设 parent，模块级 `_live_workers` 强引用代持，`finished` 后自 `deleteLater`
- 流式中断不能只靠标志位：`abort()` 还要 `stream.close()` 关掉底层 HTTP 流，否则线程会阻塞在 `next()` 等下一个 token；中断后 `run()` 内所有出口都检查 `_aborted`，保证不再 emit 任何信号（避免往已销毁的对话框发信号）
- 离屏测试 QApplication 必须 `setQuitOnLastWindowClosed(False)`，否则场景里「关闭对话框」那一步会直接让 `app.exec()` 返回，后续定时器场景全部不执行（表现为测试只跑到一半还显示全 PASS）
- delta 刷新不能每个 token 重绘：`_pending_text` 缓冲 + 50ms 单次 QTimer 统一 `insertPlainText`，与气泡刷新同一思路

- PySide6 6.12 的 `QMovie` 没有 `setLoopCount`：单次/完整播完靠 `frameChanged` 检测末帧（`_on_one_shot_frame`）+ 可选 `*_max_ms` 定时截断双保险；click/lost/random 共用此机制（见 `ONE_LOOP_STATES`）
- 随机动画「完整播一遍」= 从首帧播到末帧即结束。当前 `assets/random/` 素材约 101 帧、单遍约 10 秒，嫌长可配 `random_max_ms` 截断
- 待机动画现在固定用 `idle` 键（stand.gif），`random_action_*` 动画只在 RANDOM 状态播放，二者不共用；进入 RANDOM 时 `_set_state` 统一 `jumpToFrame(0)` 保证每次从头完整播
- 拖动偏移量 `_drag_offset` 必须在 mousePressEvent 里用「按下点全局坐标 − 窗口左上角」算一次，拖动中重算会导致窗口跳到鼠标左上方
- 斜向速度是浮点，直接对位置取整会因分量 <1px 而卡住，需用小数累加器（`_walk_fx/_walk_fy`）
- PySide6 的方法不能像普通 Python 方法那样被类属性覆盖：给 `QMenu.exec = fake` 打桩后实例调用仍走 C++ 原生实现（进嵌套事件循环卡死）；且程序化 `action.trigger()` 不会让 `menu.exec()` 返回该动作（即使随后 `close()`，exec 也返回 None），只有真实鼠标点击才返回被点动作。菜单测试因此拆两层：`_build_context_menu()` 验证菜单项与回调映射，`_exec_menu(menu, pos)` 这层用实例属性替换来喂入「被点中的动作」走完 `contextMenuEvent` 分发，真实路径仍是 `menu.exec(pos)`
- 对话框「点外部即关」要用 `event()` 拦 `QEvent.Type.WindowDeactivate` 调 `self.close()`，不能用 `focusOutEvent`（它只在整个窗口失焦时触发，子控件之间切换焦点不会走这里，且窗口从未激活过时也不触发）
- 顶层窗口 `move()` 定位的是窗口外框（frame），`geometry()` 是客户区：先 `show()` 拿到真实 `frameGeometry()` 再做屏幕钳制，否则客户区会溢出屏幕几像素（离屏 800×800 下实测 geometry 右边界 802）
- 无边框对话框不要再加 `Qt.WindowDoesNotAcceptFocus`，否则点外部（窗口失活）关闭会失效
- QWidget 的 QSS `border-radius` 不裁剪子控件：内层布局 margin 要 ≥ 圆角半径（12px），否则子控件直角盖住圆角；圆角外不出现黑角靠 `WA_TranslucentBackground`
- `QGraphicsDropShadowEffect` 加在内层白底容器上（不是外层），外层必须留 margin（20px），否则阴影被裁
- 对话框拖动只把 eventFilter 绑在 header 顶部行，标题 QLabel 设 `WA_TransparentForMouseEvents`；绑整个窗口会导致输入框选字时窗口乱跑
- `Qt.Tool` 窗口不参与 QApplication 的「最后一个窗口关闭」判定：桌宠是 Tool、对话框是唯一普通窗口时，关掉对话框会连带退出整个程序（表现为一点小叉/点形象就闪退）；桌面常驻程序必须 `app.setQuitOnLastWindowClosed(False)`（main.py），退出只走菜单「退出」（`QApplication.quit`）
- 「点外部即关」的对话框 + 常驻桌宠组合：Tool 窗口一点击就抢激活 → 按下瞬间对话框就收到 WindowDeactivate 被关掉，联动拖动根本来不及开始；桌宠必须带 `WindowDoesNotAcceptFocus`（不抢激活）。注意 WindowDeactivate 在按下瞬间就到、早于拖动判定，无法可靠区分「点一下」和「拖动」，所以对话框开着时点桌宠一律不再关闭对话框，关闭只留 ×/Esc/点其他应用三条路
- 拖动钳制必须按「窗口外框」算：`move()` 收的是 frame 左上角（`_drag_offset` 也是 `frameGeometry().topLeft()` 推的），所以用 `widget.frameGeometry()` 的副本 `moveTo(目标)` 再取坐标去比 `availableGeometry()`，拿客户区 `geometry()` 会差边框像素；另外窗口某方向尺寸 ≥ 屏幕可用区时要改成直接对齐 `screen.x()/y()`，否则 `min(max(x, ...), ...)` 会因上下界颠倒把位置钳得更靠外
- git 全局配置 `http.sslverify=false` 是必需的，不能删：Watt Toolkit（Steam++）加速 GitHub 时会把 hosts 里 `github.com` 等域名指向 `127.0.0.1` 并用自带 `SteamTools Certificate` 做中间人代理，而 git 用自己的 CA bundle（不含该证书），开启校验会报 `SSL peer certificate or SSH remote key was not OK`，导致 push/fetch 失败
- 「两个窗口联动拖动」不能各自独立位移/各自钳制：分别钳会把两窗口往同一屏角挤、直接重叠；正确做法是合成「刚性堆叠」（锚点 + 停靠侧推另一方 → 顶到上/下边框翻面 → 组合外框整体平移 `_pair_shift`），且翻面/钳制一旦改写了落位，**必须按实际落位重算被拖方的 `_drag_offset`**（桌宠在 `mouseMoveEvent`、对话框在 `ChatDialog.eventFilter`），否则下一次 move 仍按旧偏移把窗口拽回原处，表现为「贴边/翻面后来回抖动」；另注意顶层窗口 `move()` 收的是 frame 左上角，`_drag_offset`/相对偏移一律用 `frameGeometry()` 算（本项目无边框窗客户区与外框恰好重合，`pos()` 才等价）
