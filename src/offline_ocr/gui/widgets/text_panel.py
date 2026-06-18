from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
import json
from typing import List
from offline_ocr.core.base import OCRResult

class TextPanel(QWidget):
    """
    右侧识别文本展示、编辑与导出面板
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._raw_results: List[OCRResult] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # 新增：当前选中区域文字单独显示与选中面板
        layout.addWidget(QLabel("当前点击选中文字 (支持鼠标拖拽划词选中和复制):"))

        self.selection_layout = QHBoxLayout()
        self.current_selection_edit = QTextEdit()
        self.current_selection_edit.setPlaceholderText("点击左侧图片上的任何文字选框，其内容将单独在此显示...")
        self.current_selection_edit.setFixedHeight(70) # 保持紧凑，适合放置1-2行被点击内容
        self.current_selection_edit.setStyleSheet("font-size: 13px; background-color: #1e1e1e; border: 1px solid #2ecc71; border-radius: 4px; padding: 4px;")

        self.btn_copy_selection = QPushButton("复制\n选中")
        self.btn_copy_selection.setFixedWidth(55)
        self.btn_copy_selection.setFixedHeight(70)
        self.btn_copy_selection.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; font-size: 12px;")
        self.btn_copy_selection.clicked.connect(self.copy_selection_text)

        self.selection_layout.addWidget(self.current_selection_edit)
        self.selection_layout.addWidget(self.btn_copy_selection)
        layout.addLayout(self.selection_layout)

        # 间隔横线，美化排版
        from PySide6.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 全部识别结果文本编辑器
        layout.addWidget(QLabel("全部识别文本结果:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("文字提取结果将在此处显示，您可以直接在此编辑修改...")
        layout.addWidget(self.text_edit)

        # 快捷按钮排版
        btn_layout = QHBoxLayout()
        self.btn_copy = QPushButton("一键复制全部")
        self.btn_copy.clicked.connect(self.copy_all_text)
        self.btn_copy.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")

        self.btn_save_txt = QPushButton("保存为 TXT")
        self.btn_save_txt.clicked.connect(self.save_as_txt)

        self.btn_save_json = QPushButton("保存为 JSON")
        self.btn_save_json.clicked.connect(self.save_as_json)

        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_save_txt)
        btn_layout.addWidget(self.btn_save_json)
        layout.addLayout(btn_layout)

    def set_selected_text(self, text: str):
        """更新当前被点击选中的文字，支持划词选中"""
        self.current_selection_edit.setText(text)
        # 获得焦点并全选，方便用户直接复制，或者通过鼠标做局部划词选中
        self.current_selection_edit.setFocus()
        self.current_selection_edit.selectAll()

    def copy_selection_text(self):
        """快速复制当前单独选中的文字"""
        text = self.current_selection_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
        else:
            QMessageBox.warning(self, "复制失败", "当前没有点击选中的文本内容！")

    def set_ocr_results(self, results: List[OCRResult]):
        """载入 OCR 结果并拼接排版展示"""
        self._raw_results = results
        if not results:
            self.text_edit.setText("未识别到任何文本内容。")
            return

        # 同 CLI 的分行拼接逻辑
        sorted_results = sorted(results, key=lambda r: (r.box[0][1], r.box[0][0]))
        lines = []
        current_line = []
        last_y = -1
        line_threshold = 15

        for r in sorted_results:
            y_coord = r.box[0][1]
            if last_y == -1:
                current_line.append(r)
                last_y = y_coord
            elif abs(y_coord - last_y) < line_threshold:
                current_line.append(r)
            else:
                current_line = sorted(current_line, key=lambda x: x.box[0][0])
                lines.append(" ".join([x.text for x in current_line]))
                current_line = [r]
                last_y = y_coord

        if current_line:
            current_line = sorted(current_line, key=lambda x: x.box[0][0])
            lines.append(" ".join([x.text for x in current_line]))

        self.text_edit.setText("\n".join(lines))

    def copy_all_text(self):
        """一键复制全部文本"""
        text = self.text_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            # 给出状态栏通知或简单的 tooltip 即可，这里我们直接弹窗或状态指示
        else:
            QMessageBox.warning(self, "复制失败", "当前无文本可复制！")

    def save_as_txt(self):
        """保存为 TXT"""
        text = self.text_edit.toPlainText()
        if not text:
            QMessageBox.warning(self, "保存失败", "当前没有文本可保存！")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "保存 TXT 文件", "", "文本文件 (*.txt)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
                QMessageBox.information(self, "成功", "文本文件保存成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def save_as_json(self):
        """保存为结构化 JSON"""
        if not self._raw_results:
            QMessageBox.warning(self, "保存失败", "当前无结构化结果可保存！")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "保存 JSON 文件", "", "JSON 文件 (*.json)")
        if file_path:
            try:
                data = []
                for r in self._raw_results:
                    data.append({
                        "text": r.text,
                        "confidence": r.confidence,
                        "box": r.box
                    })
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "成功", "JSON 文件保存成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")
