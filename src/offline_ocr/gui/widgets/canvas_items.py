from PySide6.QtWidgets import QGraphicsObject, QApplication
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QCursor

class InteractiveBoxItem(QGraphicsObject):
    """
    可交互、有高亮悬浮效果和点击复制的 OCR 检测框。
    采用 QGraphicsObject 以原生支持 Signal。
    """
    clicked = Signal(str, float)

    def __init__(self, rect: QRectF, text: str, confidence: float):
        super().__init__()
        self.rect = rect
        self.text = text
        self.confidence = confidence

        # 默认样式：半透明绿色虚线框，微弱背景填充
        self.normal_pen = QPen(QColor(46, 204, 113, 120), 1.5, Qt.DashLine)
        self.normal_brush = QBrush(QColor(46, 204, 113, 20))

        # 悬浮样式：实线鲜绿色，较明显的透明填充
        self.hover_pen = QPen(QColor(46, 204, 113, 255), 2, Qt.SolidLine)
        self.hover_brush = QBrush(QColor(46, 204, 113, 50))

        self.current_pen = self.normal_pen
        self.current_brush = self.normal_brush

        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setToolTip(f"内容: {self.text}\n置信度: {self.confidence:.2%}\n[双击或点击此框可复制文字]")

    def boundingRect(self) -> QRectF:
        return self.rect

    def paint(self, painter, option, widget=None):
        painter.setPen(self.current_pen)
        painter.setBrush(self.current_brush)
        painter.drawRect(self.rect)

    def hoverEnterEvent(self, event):
        self.current_pen = self.hover_pen
        self.current_brush = self.hover_brush
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.current_pen = self.normal_pen
        self.current_brush = self.normal_brush
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.text)
            self.clicked.emit(self.text, self.confidence)
        super().mousePressEvent(event)
