# OWGameTrans - 守望先锋聊天实时翻译

[English](#english) | [中文](#中文)

---

## 中文

守望先锋游戏内聊天实时翻译工具。通过 OCR 屏幕捕获 + 透明叠加窗口，安全地翻译玩家手动输入的聊天消息。

### 特性

- **零封号风险** — 纯屏幕捕获 + 透明窗口，与 OBS/Discord 原理相同，不读取游戏内存、不注入 DLL
- **轻量低占用** — 运行内存 <150MB，CPU 占用 <3%，安装包 <50MB
- **实时翻译** — 500ms 扫描间隔，翻译延迟 <500ms
- **混合翻译** — 火山翻译（主）+ 百度翻译（备），国内直连，免费额度充足
- **智能过滤** — 自动过滤系统消息（英雄切换、加入/离开等），仅翻译玩家手动输入
- **双向翻译** — 外服聊天 → 中文（读），中文 → 外服语言（写）
- **一键启动** — 首次使用引导，无需技术背景

### 快速开始

#### 环境要求

- Windows 10/11
- Python 3.10+
- 守望先锋（无边框窗口模式）

#### 安装

```bash
git clone https://github.com/hzh1117/OWgametrans.git
cd OWGameTrans
pip install -r requirements.txt
```

#### 运行

```bash
python main.py
```

首次运行会弹出设置向导：
1. 拖动框选游戏聊天区域
2. 选择翻译目标语言
3. 完成设置

#### 翻译 API 配置

程序内置共享密钥可直接使用。如需更高额度，可自行注册免费 API：

- **火山翻译**：https://www.volcengine.com/product/translate
- **百度翻译**：https://fanyi-api.baidu.com/

在设置界面中填入你的 App ID 和 App Key 即可。

### 快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl+T` | 手动翻译当前可见聊天 |
| `Ctrl+Shift+T` | 打开输入辅助（中文 → 目标语言） |

### 技术架构

```
屏幕捕获 (mss/GDI) → 图像预处理 → Windows OCR → 消息解析 → 系统过滤 → 去重 → 翻译API → 叠加窗口
```

| 组件 | 技术 |
|---|---|
| 屏幕捕获 | mss (GDI BitBlt) |
| OCR | Windows.Media.Ocr (winocr) |
| 翻译 | 火山翻译 API + 百度翻译 API |
| 界面 | PyQt6 |
| 打包 | PyInstaller |

### 项目结构

```
OWGameTrans/
├── main.py                    # 主入口
├── config/                    # 配置管理
├── capture/                   # 屏幕捕获
├── ocr/                       # OCR 引擎
├── parser/                    # 消息解析与过滤
├── translate/                 # 翻译引擎
├── overlay/                   # 叠加窗口与区域选择
├── ui/                        # GUI 与系统托盘
├── cache/                     # 消息去重缓存
└── utils/                     # 工具函数
```

### 反作弊合规声明

**本工具不与守望先锋游戏进程进行任何交互。** 技术实现如下：

1. **截图方式**：使用 [mss](https://github.com/BoboTiG/python-mss) 库（底层 Windows BitBlt API）从桌面合成器（DWM）的输出缓冲区复制像素。不读取游戏进程内存，不注入 DLL，不 Hook 游戏渲染管线。此方式与 OBS Studio 的窗口采集原理相同。

2. **OCR 识别**：使用 Windows 原生 OCR 引擎（Windows.Media.Ocr）对截图进行文字识别，纯离线处理，不上传图像数据。

3. **翻译显示**：使用 PyQt6 创建透明悬浮窗口（`WindowTransparentForInput` + `WindowStaysOnTopHint`），不与游戏窗口交互，不拦截游戏输入。

4. **热键方式**：使用 `keyboard` 库（底层 `WH_KEYBOARD_LL` 低级键盘钩子）注册全局快捷键。这是 Windows 标准 API。

**反作弊合规性**：
- 不读取游戏进程内存（无 `OpenProcess`/`ReadProcessMemory`）
- 不注入 DLL 到游戏进程（无 `CreateRemoteThread`）
- 不 Hook DirectX/OpenGL 渲染管线
- 不使用 Cheat Engine 类技术
- 不加载内核驱动

**已知限制**：
- 如果游戏以管理员权限运行，请以管理员权限启动本工具（否则热键可能失效）
- 需要安装对应语言的 Windows OCR 语言包（设置 → 时间和语言 → 语言）

### 病毒误报说明

打包后的 exe 可能被 Windows Defender 或其他杀毒软件误报为病毒。这是 Python 打包工具（PyInstaller）的已知问题，非本工具独有。

**解决方法**：
1. 打开 Windows 安全中心 → 病毒和威胁防护 → 管理设置
2. 在"排除项"中添加本工具所在文件夹
3. 或在 PowerShell 中执行：
   ```powershell
   Add-MpExclusion -Path "C:\path\to\OWGameTrans"
   ```

本工具源码完全开源，不包含任何恶意代码。

### 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## English

Real-time in-game chat translation tool for Overwatch. Safely translates player-typed chat messages using OCR screen capture + transparent overlay window.

### Features

- **Zero ban risk** — Pure screen capture + transparent window, same approach as OBS/Discord
- **Lightweight** — <150MB RAM, <3% CPU, <50MB installer
- **Real-time** — 500ms scan interval, <500ms translation latency
- **Hybrid translation** — Volcengine (primary) + Baidu (fallback)
- **Smart filtering** — Auto-filters system messages, only translates player chat
- **Bidirectional** — Foreign chat → Chinese (read), Chinese → target language (write)
- **One-click setup** — Guided wizard, no technical background needed

### Quick Start

#### Requirements

- Windows 10/11
- Python 3.10+
- Overwatch (borderless windowed mode)

#### Install

```bash
git clone https://github.com/hzh1117/OWgametrans.git
cd OWGameTrans
pip install -r requirements.txt
```

#### Run

```bash
python main.py
```

### License

MIT License - see [LICENSE](LICENSE)
