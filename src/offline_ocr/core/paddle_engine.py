import os
import logging
from typing import List, Tuple, Dict, Any
from offline_ocr.core.base import BaseOCREngine, OCRResult

# 设置 Paddle 日志等级以避免过多无用输出
os.environ["PPOCR_LOG_LEVEL"] = "WARNING"
# 规避 Intel 平台 oneDNN 在处理 PIR 模型属性时的底层 C++ 执行器 Bug
os.environ["FLAGS_use_onednn"] = "0"

class PaddleOCREngine(BaseOCREngine):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lang = config.get("lang", "ch")
        self.use_gpu = config.get("use_gpu", False)
        self.models_dir = config.get("models_dir", None)
        self.ocr_client = None
        self._init_engine()

    def _init_engine(self):
        try:
            from paddleocr import PaddleOCR
            # 常见语言映射
            # ch -> 中文, en -> 英文
            # 1. 禁用 enable_mkldnn=False 彻底规避 Intel 平台 oneDNN 在处理 PIR 模型时的底层 C++ 执行器崩溃 Bug
            # 2. 禁用 use_doc_unwarping=False, use_doc_orientation_classify=False。最新版 PaddleOCR 默认开启了“智能纸张拉直”和“文档朝向判定”（UVDoc模型），
            #    这会对标准的游戏界面截图和效果图造成肉眼不可察觉的后台透视畸变拉伸，导致提取的文字坐标相对于未拉伸的原图产生微观偏移错位。
            #    关闭它们可使图片在识别时保持 100% 原始像素完整度，不仅根治了选框偏移，还能大幅加快识别速度并减少内存占用。
            self.ocr_client = PaddleOCR(
                use_textline_orientation=True,
                lang=self.lang,
                enable_mkldnn=False,
                use_doc_unwarping=False,
                use_doc_orientation_classify=False
            )
        except Exception as e:
            logging.error(f"Failed to initialize PaddleOCR: {e}")
            self.ocr_client = None

    def is_available(self) -> bool:
        return self.ocr_client is not None

    def extract_text(self, image_path: str) -> List[OCRResult]:
        if not self.is_available():
            raise RuntimeError("PaddleOCR engine is not initialized or available.")

        # 执行文字提取
        results = self.ocr_client.ocr(image_path)

        ocr_results = []
        if not results or len(results) == 0:
            return ocr_results

        # 兼容最新版 PaddleOCR 3.7.0 (PaddleX 架构) 与老版本的返回值格式
        page_res = results[0]

        # 1. 如果返回的是新版 PaddleX dict-like 对象
        if hasattr(page_res, "get") or isinstance(page_res, dict):
            # 新版存储于 rec_texts, rec_scores, rec_boxes 中
            rec_texts = page_res.get("rec_texts", []) if hasattr(page_res, "get") else page_res.get("rec_texts", [])
            rec_scores = page_res.get("rec_scores", []) if hasattr(page_res, "get") else page_res.get("rec_scores", [])

            # 优先使用二维坐标点集 rec_polys / dt_polys
            rec_polys = page_res.get("rec_polys", []) if hasattr(page_res, "get") else page_res.get("rec_polys", [])
            if len(rec_polys) == 0:
                rec_polys = page_res.get("dt_polys", []) if hasattr(page_res, "get") else page_res.get("dt_polys", [])

            # 如果没有 polys 则退而求其次使用一维 bounds [xmin, ymin, xmax, ymax] 的 rec_boxes 并展开
            rec_boxes = page_res.get("rec_boxes", []) if hasattr(page_res, "get") else page_res.get("rec_boxes", [])

            for idx, (text, score) in enumerate(zip(rec_texts, rec_scores)):
                box = []
                # 优先获取对应的 poly 顶点集
                if len(rec_polys) > idx:
                    poly_data = rec_polys[idx] # (4, 2) 的二维点
                    box = [(int(pt[0]), int(pt[1])) for pt in poly_data]
                # 否则使用 1D 形式的 box_data: [xmin, ymin, xmax, ymax]
                elif len(rec_boxes) > idx:
                    box_data = rec_boxes[idx]
                    if len(box_data) == 4:
                        # 展开为矩形的四个顺时针顶点
                        xmin, ymin, xmax, ymax = int(box_data[0]), int(box_data[1]), int(box_data[2]), int(box_data[3])
                        box = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
                    elif len(box_data) == 8:
                        box = [
                            (int(box_data[0]), int(box_data[1])),
                            (int(box_data[2]), int(box_data[3])),
                            (int(box_data[4]), int(box_data[5])),
                            (int(box_data[6]), int(box_data[7]))
                        ]

                # 如果都没有，则提供一个空框兜底
                if not box:
                    box = [(0, 0), (0, 0), (0, 0), (0, 0)]

                # 对中文转码进行安全解析
                try:
                    text_decoded = text.encode('utf-8').decode('utf-8')
                except:
                    text_decoded = text

                ocr_results.append(OCRResult(text=text_decoded, confidence=float(score), box=box))

        # 2. 如果返回的是老版本嵌套列表格式 [[[ [box_coords], (text, confidence) ], ...]]
        else:
            for line in page_res:
                box_data = line[0]  # [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
                text_data = line[1] # (text, confidence)

                box = [(int(pt[0]), int(pt[1])) for pt in box_data]
                text = text_data[0]
                confidence = float(text_data[1])

                ocr_results.append(OCRResult(text=text, confidence=confidence, box=box))

        return ocr_results

        return ocr_results
