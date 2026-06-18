from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
    QApplication
)
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPixmap, QColor, QPen, QBrush, QCursor
from typing import List, Tuple
from offline_ocr.core.base import OCRResult
from offline_ocr.gui.widgets.canvas_items import InteractiveBoxItem

class InteractiveCanvas(QGraphicsView):
    """
    可缩放、拖拽和交互的图片及 OCR 边框覆盖画布
    """
    box_clicked = Signal(str, float)  # 信号: (点击的文字, 置信度)
    file_dropped = Signal(str)        # 信号: (拖入并释放的文件路径)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 视图设置
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 关键配置：使当前 View 允许接收外部拖拽释放事件
        self.setAcceptDrops(True)

        self.pixmap_item = None
        self.box_items: List[InteractiveBoxItem] = []
        self._zoom_factor = 1.15

        # 设置画布底色
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))

    # 重写 Qt 拖拽进入、移动和释放事件
    def dragEnterEvent(self, event):
        """拖拽进入画布区域"""
        if event.mimeData().hasUrls():
            # 获取拖入的文件列表并检查后缀名
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".pdf")):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """拖拽在画布区域中移动"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        """释放拖入的文件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".pdf")):
                    # 发射信号，由 MainWindow 统一执行文件加载与 PDF 解析流程
                    self.file_dropped.emit(file_path)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def load_image(self, image_path: str):
        """载入图片并自动适应视口"""
        self.clear_canvas()
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return

        # 核心关键修复：强制将 QPixmap 的设备像素比（Device Pixel Ratio）设置为 1.0！
        # 在 Windows 高 DPI/高分屏（如 125%、150% 缩放）下，Qt 会默认将 QPixmap 的比例设置为系统的缩放比。
        # 这会导致图片在 QGraphicsScene 中的逻辑尺寸被缩小（例如 1920x1080 的图片在 150% 缩放下被当成 1280x720 逻辑尺寸渲染），
        # 而 PaddleOCR 返回的始终是绝对物理像素坐标（1920x1080）。这会导致选框等比偏大、整体向右下方偏移。
        # 强制将 QPixmap 视为 1:1 的 1.0 物理比例，可彻底消除高分屏引发的所有缩放对齐偏移。
        pixmap.setDevicePixelRatio(1.0)

        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(QRectF(pixmap.rect()))

        # 让图片适应当前窗口
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def clear_canvas(self):
        """清空画布上的图片和所有的 OCR 覆盖边框"""
        # 注意：因为 box_items 的父节点已被设为 pixmap_item，
        # 当 pixmap_item 被从 scene 中清除或 scene 被 clear 时，子项会自动销毁。
        # 我们在这里显式清空 box_items 引用即可
        self.scene.clear()
        self.pixmap_item = None
        self.box_items.clear()

    def draw_ocr_results(self, results: List[OCRResult]):
        """在图片上绘制半透明的 OCR 识别框"""
        if not self.pixmap_item:
            return

        # 清除原有的识别框
        for item in self.box_items:
            try:
                self.scene.removeItem(item)
            except:
                pass
        self.box_items.clear()

        for r in results:
            # 兼容 PaddleOCR 倾斜的多边形，转为包裹性外接矩形
            xs = [pt[0] for pt in r.box]
            ys = [pt[1] for pt in r.box]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            w = max_x - min_x
            h = max_y - min_y

            # 创建交互式覆盖矩形框
            rect_item = InteractiveBoxItem(QRectF(min_x, min_y, w, h), r.text, r.confidence)
            # 关键修复：将识别选框的父对象（Parent Item）绑定为 pixmap_item！
            # 这能让选框坐标严格对齐图片物理坐标系，随图片一起平移、缩放，杜绝相对位移和错位。
            rect_item.setParentItem(self.pixmap_item)
            rect_item.setCursor(QCursor(Qt.PointingHandCursor))

            # 连接点击信号
            rect_item.clicked.connect(self.on_box_clicked)

            self.box_items.append(rect_item)

    def on_box_clicked(self, text: str, confidence: float):
        self.box_clicked.emit(text, confidence)

    def wheelEvent(self, event):
        """滚轮缩放图片"""
        if self.pixmap_item is None:
            return super().wheelEvent(event)

        if event.angleDelta().y() > 0:
            self.scale(self._zoom_factor, self._zoom_factor)
        else:
            self.scale(1.0 / self._zoom_factor, 1.0 / self._zoom_factor)

