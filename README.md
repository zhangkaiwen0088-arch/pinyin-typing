# 拼音打字练习

一个用 Python + Tkinter 编写的整句拼音打字练习工具。上方显示中文句子，当前正在输入的字会高亮；下方输入整句拼音，完成后自动显示用时和速度。支持亮色/暗色主题与可调字号。

| 亮色主题 | 暗色主题 |
|---|---|
| ![亮色主题](docs/theme-light.png) | ![暗色主题](docs/theme-dark.png) |

## 功能

- 整句连续输入拼音，不需要逐字回车。
- 当前字高亮，已完成的字变绿，标点自动跳过。
- 输错时输入框变红，按 Backspace 修改即可。
- 第一次输入字母时开始计时，整句完成时停止。
- 实时显示进度和速度（字/分），完成后按 Enter 进入下一句。
- 内置 72 句练习，随机不重复；可随时编辑题库并重新加载。
- 亮色 / 暗色两种配色，设置会自动保存。
- 字号可在 32–96 之间调整，默认 56，适合大屏练习。
- 拼音按词组上下文生成，能正确处理“银行、音乐、重庆、山重水复”等多音字。

## 运行环境

本项目使用本机 `C:\py` 下的 Python 环境：

```text
C:\py\.pixi\envs\default\python.exe
Python 3.14.7
Tk 8.6
pypinyin 0.55.0
```

`pypinyin` 已经装入 `C:\py` 环境。若需要重新安装：

```powershell
cd C:\py
pixi add pypinyin
```

## 启动

双击项目根目录的 `run.bat` 即可启动（无控制台窗口）。

调试时使用 `run-debug.bat`，可以查看 Python 控制台错误。

也可以直接运行：

```powershell
& "C:\py\.pixi\envs\default\python.exe" .\main.py
```

## 玩法

1. 启动后用英文输入状态直接输入当前句子的拼音。
2. **不需要输入声调**，例如“你好”输入 `ni hao` 或 `nihao`。
3. 空格、撇号和英文标点会自动忽略；中文标点不用输入，输入到前一个字后会自动跳过。
4. `ü` 可以输入为 `v`，例如“绿色”输入 `lvse`。
5. 当前字显示为亮黄色底块；输错时下方状态会提示，按 Backspace 删除错误字母。
6. 整句输入完成后计时停止，按 Enter 开始下一句。

> 如果输入中文没有反应，请把输入法切换到英文模式。

## 字号与主题

- 点击右上角 `A−` / `A+` 调整字号，范围 32–96，默认 56。
- 也可以按 `Ctrl + 鼠标滚轮`，或 `Ctrl+=` / `Ctrl+-`。
- 点击“亮色”/“暗色”切换配色，选择会保存在 `.settings.json` 中，下次启动继续使用。
- 拼音输入区字号会跟随中文字号自动缩放。

## 编辑题库

题库文件是项目根目录的 `sentences.txt`，UTF-8 编码，一行一句：

```text
# 以 # 开头的是注释，空行会被忽略
今天天气真好，我们一起去公园散步吧。
窗外的雨声让我想起小时候的夏天。
```

添加或修改后，回到应用中点击“重新加载题库”（或按 `F5`）。也可以点击“打开题库”直接编辑。

- 重复句子和无法解析的行会被跳过，并在加载时提示。
- 建议一句一行，使用正常中文标点，pypinyin 能更准确地进行词组切分。
- 题库内置日常、自然、学习工作、旅行美食、成语诗词、绕口令和生活感悟等分类，当前共 72 句。

## 快捷键

| 按键 | 功能 |
|---|---|
| `Backspace` | 删除错误字母 |
| `Enter` | 完成后进入下一句 |
| `Ctrl + R` | 重开当前句并清零计时 |
| `F5` | 重新加载题库 |
| `Ctrl + 鼠标滚轮` | 调整字号 |
| `Ctrl + =` / `Ctrl + -` | 放大 / 缩小字号 |

## 项目结构

```text
pinyin-typing/
├─ main.py              # 入口、DPI 和错误提示
├─ app.py               # Tkinter 界面、主题、计时器
├─ trainer.py           # 拼音生成、输入判定、题库解析
├─ sentences.txt        # 可直接编辑的题库
├─ docs/                # 亮色/暗色界面预览
├─ tests/
│  └─ test_trainer.py   # 22 个核心逻辑测试
├─ run.bat              # 正常启动（pythonw）
├─ run-debug.bat        # 调试启动（显示控制台）
├─ requirements.txt
└─ .gitignore
```

`.settings.json` 是运行后自动生成的本地配置，已被 Git 忽略。

## 测试

```powershell
cd C:\Users\kaiwen\Documents\deepseek-harness\default-workspace\pinyin-typing
& "C:\py\.pixi\envs\default\python.exe" -m unittest discover -s tests -v
```

当前测试覆盖句子解析、多音字、标点跳过、输入规范化、错误定位、计时格式、随机不重复和题库加载。
