import os
from typing import List
from PIL import Image

def pdf_to_images(pdf_path: str, output_dir: str) -> List[str]:
    """
    将 PDF 转换为图片保存在指定目录下
    返回保存的图片路径列表
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError("pdf2image library is required for PDF OCR processing. Install it or ensure Poppler is in system path.")

    # 转换 pdf 为 PIL images
    pages = convert_from_path(pdf_path, dpi=200)
    image_paths = []

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    for i, page in enumerate(pages):
        img_name = f"{base_name}_page_{i + 1}.png"
        img_path = os.path.join(output_dir, img_name)
        page.save(img_path, "PNG")
        image_paths.append(img_path)

    return image_paths
