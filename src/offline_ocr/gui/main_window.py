import sys
import os
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFileDialog,
    QMessageBox, QProgressBar, QStatusBar, QApplication, QSplitter
)
from PySide6.QtCore import Qt

from offline_ocr.gui.widgets.sidebar import Sidebar
from offline_ocr.gui.widgets.canvas import InteractiveCanvas
from offline_ocr.gui.widgets.text_panel import TextPanel
from offline_ocr.gui.threads import OCRWorker
from offline_ocr.utils.image_utils import deskew, enhance_contrast
from offline_ocr.utils.pdf_utils import pdf_to_images

class MainWindow(QMainWindow):
    """
    OCR 主窗口，负责界面调度和多线程管控
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("全能离线 OCR 文字提取工具 (PaddleOCR / PySide6)")
        self.resize(1200, 800)

        self.current_image_path = None
        self.temp_processed_path = None
        self.temp_pdf_dir = None
        self.ocr_thread = None

        self.init_ui()

    def init_ui(self):
        # 核心中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 整体采用水平布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # 1. 左侧边栏 (固定宽度)
        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(280)
        self.sidebar.open_image_clicked.connect(self.select_file)
        self.sidebar.run_ocr_clicked.connect(self.start_ocr)
        main_layout.addWidget(self.sidebar)

        # 2. 右侧区域，使用 QSplitter 允许用户动态拖拽缩放
        splitter = QSplitter(Qt.Horizontal)

        # 中间交互画布
        self.canvas = InteractiveCanvas()
        self.canvas.box_clicked.connect(self.on_box_clicked)
        # 连接拖拽释放信号
        self.canvas.file_dropped.connect(self.load_file)
        splitter.addWidget(self.canvas)

        # 右侧文本编辑器和保存面板
        self.text_panel = TextPanel()
        splitter.addWidget(self.text_panel)

        # 设置比例，画布 65%, 文本面板 35%
        splitter.setSizes([750, 400])
        main_layout.addWidget(splitter)

        # 3. 状态栏和进度条
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.status_bar.showMessage("准备就绪。请载入图片或 PDF 文件。")

    def select_file(self):
        """打开文件对话框选择图片或 PDF"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片或 PDF", "",
            "支持的文件 (*.png *.jpg *.jpeg *.bmp *.pdf)"
        )
        if not file_path:
            return

        self.load_file(file_path)

    def load_file(self, file_path: str):
        """通用文件加载方法（支持文件选择与拖拽释放）"""
        self.current_image_path = file_path
        self.status_bar.showMessage(f"已载入文件: {os.path.basename(file_path)}")

        # 判定是否是 PDF
        if file_path.lower().endswith(".pdf"):
            import tempfile
            import shutil
            # 如果已有 PDF 目录缓存，先进行清理
            if self.temp_pdf_dir:
                try:
                    self.temp_pdf_dir.cleanup()
                except:
                    pass
            # 临时生成一个转换后图片的缓存
            self.temp_pdf_dir = tempfile.TemporaryDirectory()
            self.status_bar.showMessage("正在将 PDF 转换为图片...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                pages = pdf_to_images(file_path, self.temp_pdf_dir.name)
                if pages:
                    # 默认加载 PDF 的第一页
                    self.current_image_path = pages[0]
                    self.canvas.load_image(self.current_image_path)
                    self.status_bar.showMessage(f"已载入 PDF: {os.path.basename(file_path)} (共 {len(pages)} 页，已加载第 1 页)")
                else:
                    QMessageBox.warning(self, "转换失败", "该 PDF 文件未包含有效的可解析页面。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"PDF 转换失败: {e}")
            finally:
                QApplication.restoreOverrideCursor()
        else:
            self.canvas.load_image(file_path)

    def start_ocr(self, engine_name: str, lang: str, use_gpu: bool, use_prep: bool):
        """开始执行 OCR 多线程逻辑"""
        if not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先载入一张图片或 PDF 文件！")
            return

        if self.ocr_thread and self.ocr_thread.isRunning():
            QMessageBox.warning(self, "提示", "OCR 任务正在运行，请等待当前任务完成。")
            return

        target_ocr_path = self.current_image_path

        # 图像预处理 (纠偏和直方图增强)
        if use_prep:
            self.status_bar.showMessage("正在执行图像增强与校正...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                from offline_ocr.utils.image_utils import safe_imwrite
                # 增强
                enhanced = enhance_contrast(self.current_image_path)
                import tempfile
                fd, self.temp_processed_path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                safe_imwrite(self.temp_processed_path, enhanced)

                # 纠偏
                rotated = deskew(self.temp_processed_path)
                safe_imwrite(self.temp_processed_path, rotated)

                target_ocr_path = self.temp_processed_path
                # 在画布上显示预处理后的效果
                self.canvas.load_image(target_ocr_path)
            except Exception as e:
                self.status_bar.showMessage(f"图像预处理失败: {e}")
            finally:
                QApplication.restoreOverrideCursor()

        # 配置参数并启动后台 Worker
        config = {
            "lang": lang,
            "use_gpu": use_gpu,
        }

        self.status_bar.showMessage("文字提取中，首次运行需要较长时间加载本地权重...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.sidebar.setEnabled(False) # 运行期间禁用侧边栏操作

        self.ocr_thread = OCRWorker("paddleocr", config, target_ocr_path)
        self.ocr_thread.progress.connect(self.progress_bar.setValue)
        self.ocr_thread.finished.connect(self.on_ocr_success)
        self.ocr_thread.error.connect(self.on_ocr_failed)
        self.ocr_thread.start()

    def on_ocr_success(self, results, elapsed_time):
        """OCR 执行成功回调"""
        self.status_bar.showMessage(f"文字提取成功！耗时 {elapsed_time:.2f} 秒。共识别 {len(results)} 个文本块。")
        self.progress_bar.setVisible(False)
        self.sidebar.setEnabled(True)

        # 1. 刷新文本面板
        self.text_panel.set_ocr_results(results)

        # 2. 画布绘制检测框
        self.canvas.draw_ocr_results(results)

        # 清除图像预处理的临时文件
        self.cleanup_temp_files()

    def on_ocr_failed(self, error_msg):
        """OCR 运行失败回调"""
        self.status_bar.showMessage("文字提取失败。")
        self.progress_bar.setVisible(False)
        self.sidebar.setEnabled(True)
        QMessageBox.critical(self, "OCR 失败", f"运行过程中遇到错误:\n{error_msg}\n\n提示：若提示 C++ 错误，请确保系统已安装 MSVC 运行库。")
        self.cleanup_temp_files()

    def on_box_clicked(self, text, confidence):
        """画布上的文本块被点击时的槽函数"""
        self.status_bar.showMessage(f"已复制文本: '{text}' (置信度: {confidence:.2%})", 3000)
        # 将被点击的文字同步显示到右侧的“当前选中文字”单独编辑框中，支持鼠标拖拽选中和局部复制
        self.text_panel.set_selected_text(text)

    def cleanup_temp_files(self):
        """清理临时图像文件"""
        if self.temp_processed_path and os.path.exists(self.temp_processed_path):
            try:
                os.remove(self.temp_processed_path)
            except:
                pass
            self.temp_processed_path = None

    def closeEvent(self, event):
        """窗口关闭时深度清理 PDF 页面临时文件夹"""
        self.cleanup_temp_files()
        if self.temp_pdf_dir:
            try:
                self.temp_pdf_dir.cleanup()
            except:
                pass
        super().closeEvent(event)

def run_gui():
    app = QApplication(sys.argv)
    # 设置 Qt 全局通用深色系样式，带来更佳的专业视觉感
    app.setStyle("Fusion")

    # 调色板
    from PySide6.QtGui import QPalette, QColor
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_gui()
