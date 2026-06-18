import cv2
import numpy as np
import os

def safe_imread(path: str) -> np.ndarray:
    """安全读取包含中文/Unicode路径的图片文件"""
    try:
        # 使用 np.fromfile 读取为二进制字节，避免 Windows 下 OpenCV C++ 引擎由于编码不支持中文路径而返回 None 的 Bug
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"OpenCV imdecode returned None for path: {path}")
        return img
    except Exception as e:
        raise ValueError(f"Cannot read image: {path}, error: {e}")

def safe_imwrite(path: str, img: np.ndarray):
    """安全保存包含中文/Unicode路径的图片文件"""
    try:
        ext = os.path.splitext(path)[1]
        is_success, buffer = cv2.imencode(ext, img)
        if not is_success:
            raise ValueError(f"Cannot encode image as {ext}")
        # 二进制写入磁盘，完全绕过 OpenCV 底层路径编码 Bug
        with open(path, "wb") as f:
            f.write(buffer.tobytes())
    except Exception as e:
        raise ValueError(f"Cannot save image to: {path}, error: {e}")

def deskew(image_path: str) -> np.ndarray:
    """自动纠偏/旋转校正"""
    img = safe_imread(image_path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return img

    angle = cv2.minAreaRect(coords)[-1]

    # OpenCV 的 minAreaRect 在不同版本下返回的角度范围不同
    # 针对原本就已经完全摆正的水平或垂直图片，防止计算出 90 或 -90 度的直角旋转误判，这会导致图片颠倒、宽高互换，
    # 最终导致 OCR 获取的旋转后坐标与画布上渲染的原图坐标发生极其严重的错位偏差。
    if abs(angle) < 0.5 or abs(angle - 90.0) < 0.5 or abs(angle + 90.0) < 0.5 or abs(angle - 180.0) < 0.5:
        return img

    # OpenCV 的 minAreaRect 返回的角度比较特殊
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # 如果偏转角极其微小，不进行校正
    if abs(angle) < 0.5:
        return img

    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

def enhance_contrast(image_path: str) -> np.ndarray:
    """对比度增强，适合低光、褶皱纸张"""
    img = safe_imread(image_path)

    # 转换为 LAB 色彩空间，对 L 通道（亮度）进行直方图自适应均衡化 (CLAHE)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return enhanced
