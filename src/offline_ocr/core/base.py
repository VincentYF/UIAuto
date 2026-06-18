from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

@dataclass
class OCRResult:
    text: str
    confidence: float
    # 4对角点坐标：[(x0, y0), (x1, y1), (x2, y2), (x3, y3)]
    box: List[Tuple[int, int]]

class BaseOCREngine(ABC):
    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """初始化 OCR 引擎"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎库和模型文件是否可用"""
        pass

    @abstractmethod
    def extract_text(self, image_path: str) -> List[OCRResult]:
        """对给定路径的图片进行文字提取"""
        pass
