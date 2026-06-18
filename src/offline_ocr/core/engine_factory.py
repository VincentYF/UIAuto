from typing import Dict, Any
from offline_ocr.core.base import BaseOCREngine
from offline_ocr.core.paddle_engine import PaddleOCREngine

class OCREngineFactory:
    @staticmethod
    def create_engine(engine_name: str, config: Dict[str, Any]) -> BaseOCREngine:
        engine_name = engine_name.lower()
        if engine_name == "paddleocr" or engine_name == "paddle":
            return PaddleOCREngine(config)
        else:
            raise ValueError(f"Unsupported OCR engine: {engine_name}")
