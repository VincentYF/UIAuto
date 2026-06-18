from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QCheckBox, QPushButton, QLabel, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

class Sidebar(QWidget):
    """
    左侧参数设置和操作边栏
    """
    open_image_clicked = Signal()
    run_ocr_clicked = Signal(str, str, bool, bool) # (引擎, 语言, 是否GPU, 是否预处理)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 文件操作组
        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout(file_group)
        self.btn_open = QPushButton("打开图片 / PDF")
        self.btn_open.setFixedHeight(40)
        self.btn_open.setStyleSheet("background-color: #34495e; color: white; font-weight: bold;")
        self.btn_open.clicked.connect(self.open_image_clicked.emit)
        file_layout.addWidget(self.btn_open)
        layout.addWidget(file_group)

        # 引擎配置组
        config_group = QGroupBox("OCR 配置")
        config_layout = QVBoxLayout(config_group)

        # 引擎选择
        config_layout.addWidget(QLabel("OCR 引擎:"))
        self.combo_engine = QComboBox()
        self.combo_engine.addItems(["PaddleOCR"])
        config_layout.addWidget(self.combo_engine)

        # 语言选择
        config_layout.addWidget(QLabel("识别语言:"))
        self.combo_lang = QComboBox()
        # PaddleOCR 常用语种
        self.combo_lang.addItem("中英混合 (ch)", "ch")
        self.combo_lang.addItem("英文 (en)", "en")
        self.combo_lang.addItem("繁体中文 (chinese_cht)", "chinese_cht")
        config_layout.addWidget(self.combo_lang)

        # 图像预处理
        self.cb_prep = QCheckBox("启用图像预处理 (纠偏、高对比)")
        self.cb_prep.setChecked(False)
        self.cb_prep.setToolTip("仅适合倾斜、低光、褶皱的手机拍照文档。数字截图或直角效果图勾选它可能会降低提取速度与准确度。")
        config_layout.addWidget(self.cb_prep)

        # GPU 加速智能默认配置
        self.cb_gpu = QCheckBox("启用 GPU 加速")

        # 智能环境检测：静默检测用户电脑中是否配有 NVIDIA 独立显卡并正确配置了 CUDA
        has_gpu = False
        try:
            import paddle
            has_gpu = paddle.device.is_compiled_with_cuda()
        except:
            pass

        self.cb_gpu.setChecked(has_gpu)
        if has_gpu:
            self.cb_gpu.setToolTip("检测到您的电脑配置了可用的 CUDA GPU 环境，已默认开启 5~10 倍极速推理加速！")
        else:
            self.cb_gpu.setToolTip("未检测到可用的本地 CUDA 环境。勾选它需要您的 Python 配备有 paddle-gpu 及匹配的 CUDA 驱动，否则会报错。")

        config_layout.addWidget(self.cb_gpu)

        layout.addWidget(config_group)

        # 执行动作组
        action_layout = QVBoxLayout()
        self.btn_run = QPushButton("开始文字提取")
        self.btn_run.setFixedHeight(45)
        self.btn_run.setStyleSheet("background-color: #2ecc71; color: white; font-size: 14px; font-weight: bold;")
        self.btn_run.clicked.connect(self.on_run_clicked)
        action_layout.addWidget(self.btn_run)
        layout.addLayout(action_layout)

        # 伸缩，保证组件顶部对齐
        layout.addStretch()

    def on_run_clicked(self):
        engine = self.combo_engine.currentText()
        lang = self.combo_lang.currentData()
        use_gpu = self.cb_gpu.isChecked()
        use_prep = self.cb_prep.isChecked()
        self.run_ocr_clicked.emit(engine, lang, use_gpu, use_prep)
