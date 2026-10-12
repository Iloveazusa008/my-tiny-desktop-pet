# Progress · AI 桌面宠物

依据 `handbook.txt` 实现，Python + PySide6。

## 当前文件结构

```
mypet/
├── handbook.txt          # 纲领性文件（只读依据）
├── progress.md           # 本文件
├── .gitignore            # 排除 __pycache__ / _test_log.txt / venv 等
├── requirements.txt      # 依赖：PySide6 / PyYAML / openai
├── start.bat             # 启动脚本（切到脚本目录，跑 main.py，出错暂停）
├── main.py               # 程序入口
├── config.yaml           # 行为与模型连接配置
├── assets/               # GIF 素材（用户提供）
│   ├── idle/stand.gif        # idle
│   ├── walk/walk-left.gif    # 向左走（水平分量向左时播放）
│   ├── walk/walk-right.gif   # 向右走（水平分量向右时播放）
│   ├── walk/get lost.gif     # 走丢（每次走完后按概率播放一次）
│   ├── click/click.gif       # click
│   ├── drag/drag.gif         # drag
│   └── random/              # 待机时随机混播的 GIF（按 idle_random_chance 概率替换 stand.gif）
│       ├── pillow talk.gif
│       └── sleepy.gif
└── src/
    ├── __init__.py
    ├── config.py         # 加载 config.yaml，解析相对动画路径为绝对路径
    └── pet_window.py     # 主窗口：无边框、透明、置顶；状态机 + 走动/点击/拖动
```

## 每个文件干什么

| 文件 | 职责 |
|---|---|
| `main.py` | 创建 QApplication，加载配置，显示 PetWindow |
| `start.bat` | 双击启动：切到脚本目录、UTF-8 代码页、运行 main.py，失败时暂停窗口便于看报错 |
| `config.py` | 读取 `config.yaml`，把 animation 里的相对路径（含列表型 `idle_random`）拼成绝对路径 |
| `src/pet_window.py` | 桌宠窗口：Frameless + WA_TranslucentBackground + WindowStaysOnTopHint + Tool；状态机 idle/walk/click/drag/lost；QMovie 播 GIF；360° 随机走动、碰边按轴反向、按水平分量切左右走 GIF；左键单击完整播 click、按住移动播 drag（跟手拖动）；每次走完按概率播 get lost.gif（走丢）后回待机；每次进待机按概率从 stand.gif 与 random/ 目录 GIF 里挑一个播 |
| `config.yaml` | 窗口尺寸、启动位置、各状态 GIF 路径、走动速度/时长/操作后延迟、click/lost 截断上限、lost 触发概率、idle_random_chance |

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
- [x] 走动延迟：上次任意操作（点击/拖动等）结束后 10~60s 随机发起走动（可配）
- [x] 左键单击完整播放 click.gif 一次后回待机（末帧检测结束；`click_max_ms: 0` 不截断，可配正值截断）
- [x] 走动中被点击/拖动：先中断走动播对应动画，操作结束后重新计时再走
- [x] `set_walk_enabled()` 开关走动（供后续右键菜单调用）
- [x] 走丢效果：每次走动结束后按概率（`lost_chance`，默认 0.3）播放 `walk/get lost.gif` 一次后回待机；支持 `lost_max_ms` 截断上限
- [x] 待机随机混播：每次进入待机按概率（`idle_random_chance`）从 `idle/stand.gif` 与 `random/` 目录 GIF 里挑一个循环播；`idle_random` 列表写在配置里，`talk`/`error` 暂留空
- [x] 修复 `config.py` 对空动画路径（`talk:`/`error:` 留空为 None）的崩溃

## 已知问题 / TODO

- [ ] `talk`、`error` GIF 未制作，配置暂留空，待素材就绪后填路径并接入状态机
- [ ] 右键菜单（开始对话 / 暂停走动 / 回到中央 / 打开配置 / 退出）未实现
- [ ] 气泡（QPainter 自绘圆角矩形+尾巴、自动换行、流式刷新）未实现
- [ ] 对话框（多轮上下文、流式输出、关闭清空、中断请求）未实现
- [ ] AI 接入（OpenAI SDK、base_url 切换、流式、失败播 error）未实现
- [ ] 气泡样式配置项缺失：圆角、边框色、填充色、透明度、字体、字号、最大宽度
- [ ] `system_prompt.txt` 人格配置文件未创建

## 版本控制（Git）

- 2026-10-12：`git init`（main 分支）初始化本仓库，新增 `.gitignore`（排除 `__pycache__/`、`*.pyc`、`_test_log.txt`、`venv/`、`.pytest_cache/`、`.ruff_cache/`）
- 2026-10-12：首次提交 `feat: 桌宠项目初始版本`，内容为代码 + 配置 + handbook + progress.md + 8 个 GIF 素材（约 11MB，纳入版本控制）
- 2026-10-12：打标签 `v1.0.0` 标记当前稳定版本
- 2026-10-12：添加远端 `origin` → `https://github.com/Iloveazusa008/my-tiny-desktop-pet.git`，`git push -u origin main --tags` 推送至 GitHub（账号 `Iloveazusa008`）

日常提交流程：`git add .` → `git commit -m "描述"` → `git push`；确认某个版本不错时可用 `git tag v1.x.x` 再 `git push --tags`。

## 备注 / 踩坑记录

- PySide6 6.12 的 `QMovie` 没有 `setLoopCount`：单击播完靠 `frameChanged` 检测末帧 + 可选 `click_max_ms` 定时截断双保险
- 拖动偏移量 `_drag_offset` 必须在 mousePressEvent 里用「按下点全局坐标 − 窗口左上角」算一次，拖动中重算会导致窗口跳到鼠标左上方
- 斜向速度是浮点，直接对位置取整会因分量 <1px 而卡住，需用小数累加器（`_walk_fx/_walk_fy`）
- git 全局配置 `http.sslverify=false` 是必需的，不能删：Watt Toolkit（Steam++）加速 GitHub 时会把 hosts 里 `github.com` 等域名指向 `127.0.0.1` 并用自带 `SteamTools Certificate` 做中间人代理，而 git 用自己的 CA bundle（不含该证书），开启校验会报 `SSL peer certificate or SSH remote key was not OK`，导致 push/fetch 失败
