import sys
import os
import time
from PySide6.QtCore import QThread, Signal
from offline_ocr.core.engine_factory import OCREngineFactory

class OCRWorker(QThread):
    """
    后台 OCR 执行线程，防止主 GUI 界面阻塞/未响应
    """
    progress = Signal(int)             # 进度比例 (0-100)
    finished = Signal(list, float)     # (结果列表, 花费时间秒)
    error = Signal(str)                # 错误信息描述

    def __init__(self, engine_name: str, config: dict, image_path: str):
        super().__init__()
        self.engine_name = engine_name
        self.config = config
        self.image_path = image_path

    def run(self):
        try:
            self.progress.emit(10)
            start_time = time.time()

            # 初始化/加载引擎
            engine = OCREngineFactory.create_engine(self.engine_name, self.config)
            self.progress.emit(40)

            # 进行文字提取
            results = engine.extract_text(self.image_path)
            self.progress.emit(90)

            elapsed = time.time() - start_time
            self.progress.emit(100)
            self.finished.emit(results, elapsed)
        except Exception as e:
            self.error.emit(str(e))
