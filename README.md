# 离线 OCR 图片/PDF 文字提取工具 (Offline OCR)

一个基于 **PaddleOCR** 与 **PySide6** (Qt for Python) 构建的现代化、全本地运行、保护隐私的离线图片和 PDF 文字提取程序。支持强大的**命令行工具 (CLI)**与直观的**图形用户界面 (GUI)**。

## ✨ 特性

- **🔒 100% 离线运行**：完全无需联网，绝不上传您的发票、文档或任何敏感图片，完美保障隐私安全。
- **🚀 极高准确率**：默认使用目前最强的高性能本地 PaddleOCR 模型，支持中英双语、繁体中文等混合识别。
- **🖥️ 交互式 GUI (图形界面)**：
  - **缩放与拖拽**：鼠标滚轮无级缩放图片，左键点击按住自由拖动。
  - **点击复制**：自动用半透明框覆盖识别文本，鼠标悬浮显示高亮和置信度，点击任何文字框即可**立即复制该区域文字**到剪贴板。
  - **PDF 支持**：直接拖入或打开 PDF 文件，自动转换为高清图片逐页解析提取。
  - **多线程运行**：提取过程在后台运行，界面绝不卡死。
  - **精致深色模式**：默认搭配专业、高对比度的现代深色系 Fusion 皮肤。
- **💻 自动化 CLI (命令行工具)**：
  - 支持对单张图片、整个文件夹中的图片、或 PDF 进行批量 OCR。
  - 支持保存为 `txt` (保持段落排版)、`json` (含坐标、置信度等结构化数据)、`md` (Markdown 列表) 以及 `csv`。
- **⚙️ 图像智能预处理**：内置自动旋转/倾斜纠偏（Deskew）以及针对低光、褶皱纸张的自适应直方图对比度增强（CLAHE）。

---

## 🛠️ 快速安装

本项目推荐使用极速 Python 包管理器 [**`uv`**](https://github.com/astral-sh/uv) 进行环境配置与运行。

### 1. 确保安装了 `uv`
如果没有 `uv`，您可以通过下面的终端命令快速安装（或使用标准 pip）：
```powershell
# Windows PowerShell
powershell -c "irm https://astral-sh/uv/install.ps1 | iex"
```

### 2. 克隆/打开本项目并创建虚拟环境
```bash
# 创建 3.10 版本的虚拟环境 (PaddleOCR 在 3.10 下运行极其稳定)
uv venv --python 3.10

# 激活虚拟环境
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat
# Linux/macOS:
source .venv/bin/activate
```

### 3. 安装依赖和本项目
```bash
# 以可编辑模式本地安装整个项目及依赖
uv pip install -e .
```

> **提示（Windows 常见问题）**：首次运行如果提示缺少 C++ 依赖或 DLL 加载错误，请确保系统已安装 Microsoft Visual C++ Redistributable 运行库。您可以通过 [微软官方链接](https://aka.ms/vs/17/release/vc_redist.x64.exe) 一键下载并安装。

---

## 🚀 使用指南

### 1. 图形化界面 (GUI)

直接启动桌面端：
```bash
# 激活虚拟环境后运行
offline-ocr-gui
```
或者使用 `python` 模块运行：
```bash
python -m offline_ocr
```

#### GUI 交互小贴士：
1. 点击左侧“**打开图片 / PDF**”，选择一张有文字的图片（如发票、截图）或 PDF 格式文档。
2. 在“OCR 配置”中可以按需勾选“**启用图像预处理**”或“**启用 GPU 加速**”（需要本地有 CUDA 环境）。
3. 点击“**开始文字提取**”。首次运行会花费数十秒在后台自动下载 PaddleOCR 的官方离线模型权重（模型保存在系统用户目录下，后续完全离线运行）。
4. 识别完成后，图片上会出现绿色虚线框：
   - **鼠标悬浮**：可直接预览提取的内容与置信度。
   - **左键单击框**：将该区域文本瞬间复制到剪贴板，并在状态栏提示。
   - **右侧面板**：支持查看与二次编辑全部合并后的文本，并可以一键复制或导出为 `TXT`/`JSON`。

---

### 2. 命令行工具 (CLI)

命令行工具非常适合批量脚本与自动化工作流：

```bash
# 查看帮助与参数
offline-ocr --help
```

#### 基本命令格式：
```bash
offline-ocr [OPTIONS] PATH
```

#### 常用实例：
* **提取单张图片文字，在控制台显示进度并保存为文本文件**：
  ```bash
  offline-ocr invoice.png
  ```
  这将在同级目录下生成 `invoice_ocr.txt`。

* **提取一个文件夹下所有图片的文字并保存为 JSON (含位置信息)**：
  ```bash
  offline-ocr -f json -o ./output_results/ ./my_images/
  ```

* **对一个多页 PDF 进行全自动转换并提取为 Markdown 格式**：
  ```bash
  offline-ocr -f md -l ch my_document.pdf
  ```

* **启用图像预处理（纠偏和增强对比度）并开启 GPU 加速**：
  ```bash
  offline-ocr --preprocessing --gpu receipt.jpg
  ```

#### CLI 可选参数列表：
* `-e, --engine [paddleocr|paddle]`：OCR 引擎，当前默认支持 paddleocr。
* `-l, --lang TEXT`：提取语言，默认为 `ch` (中英混合)，支持 `en` 等多语种。
* `-o, --output-dir PATH`：输出结果保存的目标目录。
* `-f, --format [txt|json|md|csv]`：输出保存格式，默认为 `txt`。
* `--gpu / --no-gpu`：是否启用 GPU 加速。
* `--preprocessing / --no-prep`：是否启用图像预处理。

---

## 📦 项目结构说明

```text
src/offline_ocr/
├── core/               # 核心 OCR 抽象及多引擎适配层
│   ├── base.py         # OCR 基础类与数据契约
│   ├── engine_factory.py # 引擎动态实例化工厂
│   └── paddle_engine.py # PaddleOCR 的具体对接实现
├── cli/                # 命令行层
│   └── main.py         # Click 实现的多格式批处理 CLI
├── gui/                # PySide6 图形界面层
│   ├── main_window.py  # 界面控制与主线程协调
│   ├── threads.py      # 防止界面卡死的后台 QThread 工作线程
│   └── widgets/        # GUI 积木组件
│       ├── canvas.py     # 支持缩放拖拽和检测框高亮点击的智能画布
│       ├── canvas_items.py # 每一个悬浮框的高亮逻辑
│       ├── sidebar.py    # 文件导入及配置面板
│       └── text_panel.py # 文字预览、编辑、复制和导出面板
└── utils/              # 通用工具层
    ├── image_utils.py  # OpenCV 纠偏、CLAHE 直方图增强等图像处理
    └── pdf_utils.py    # pdf2image 高清 PDF 转图片工具
```

---

## 📝 许可证

本项目基于 [MIT 许可证](LICENSE) 开源，允许自由修改与商用。
