import os
import sys
import json
import click
import cv2
from typing import List
from offline_ocr.core.engine_factory import OCREngineFactory
from offline_ocr.core.base import OCRResult
from offline_ocr.utils.image_utils import deskew, enhance_contrast
from offline_ocr.utils.pdf_utils import pdf_to_images

def save_text(results: List[OCRResult], output_path: str):
    """保存为纯文本，尽可能保持排版段落"""
    # 按照 y 轴坐标，再按 x 轴坐标对文字框进行简单排序
    sorted_results = sorted(results, key=lambda r: (r.box[0][1], r.box[0][0]))

    # 简单的分行重构算法
    lines = []
    current_line = []
    last_y = -1
    line_threshold = 15  # y 轴距离在 15 像素内的视为同一行

    for r in sorted_results:
        y_coord = r.box[0][1]
        if last_y == -1:
            current_line.append(r)
            last_y = y_coord
        elif abs(y_coord - last_y) < line_threshold:
            current_line.append(r)
        else:
            # 排序当前行并拼接
            current_line = sorted(current_line, key=lambda x: x.box[0][0])
            lines.append(" ".join([x.text for x in current_line]))
            current_line = [r]
            last_y = y_coord

    if current_line:
        current_line = sorted(current_line, key=lambda x: x.box[0][0])
        lines.append(" ".join([x.text for x in current_line]))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def save_json(results: List[OCRResult], output_path: str):
    """保存为结构化 JSON 格式，保留坐标和置信度"""
    data = []
    for r in results:
        data.append({
            "text": r.text,
            "confidence": r.confidence,
            "box": r.box
        })
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_markdown(results: List[OCRResult], output_path: str):
    """保存为 markdown 格式"""
    # 同行合并并输出为 markdown 列表或简单块
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
            lines.append("- " + " ".join([x.text for x in current_line]))
            current_line = [r]
            last_y = y_coord

    if current_line:
        current_line = sorted(current_line, key=lambda x: x.box[0][0])
        lines.append("- " + " ".join([x.text for x in current_line]))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# OCR 提取结果\n\n" + "\n".join(lines))

def save_csv(results: List[OCRResult], output_path: str):
    """保存为 csv 格式"""
    import csv
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "confidence", "x0", "y0", "x1", "y1", "x2", "y2", "x3", "y3"])
        for r in results:
            writer.writerow([
                r.text,
                f"{r.confidence:.4f}",
                r.box[0][0], r.box[0][1],
                r.box[1][0], r.box[1][1],
                r.box[2][0], r.box[2][1],
                r.box[3][0], r.box[3][1]
            ])

@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("-e", "--engine", type=click.Choice(["paddleocr", "paddle"]), default="paddleocr", help="OCR 引擎，当前默认支持 paddleocr")
@click.option("-l", "--lang", default="ch", help="提取语言: ch (中英), en (纯英) 等")
@click.option("-o", "--output-dir", type=click.Path(), default=None, help="提取结果保存的目标目录（默认与输入相同）")
@click.option("-f", "--format", type=click.Choice(["txt", "json", "md", "csv"]), default="txt", help="输出保存格式")
@click.option("--gpu/--no-gpu", default=False, help="是否启用 GPU 加速")
@click.option("--preprocessing/--no-prep", default=False, help="是否启用图像预处理（纠偏和增强对比度）")
def main(path: str, engine: str, lang: str, output_dir: str, format: str, gpu: bool, preprocessing: bool):
    """
    离线图片/PDF OCR 文字提取 CLI 工具。
    """
    click.echo(f"正在加载 {engine} 引擎...", err=True)
    config = {
        "lang": lang,
        "use_gpu": gpu,
    }

    try:
        ocr_engine = OCREngineFactory.create_engine(engine, config)
    except Exception as e:
        click.echo(f"引擎加载失败: {e}", err=True)
        sys.exit(1)

    # 确定要处理的图片文件列表
    targets = []
    temp_dir = None
    is_pdf = path.lower().endswith(".pdf")

    if is_pdf:
        import tempfile
        temp_dir = tempfile.TemporaryDirectory()
        click.echo("正在解析 PDF 页面...", err=True)
        try:
            targets = pdf_to_images(path, temp_dir.name)
        except Exception as e:
            click.echo(f"PDF 转换图片失败: {e}", err=True)
            sys.exit(1)
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):
                    targets.append(os.path.join(root, file))
    else:
        targets.append(path)

    if not targets:
        click.echo("没有找到可处理的有效图片文件。", err=True)
        sys.exit(0)

    # 确定输出目录
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = os.path.dirname(os.path.abspath(path)) if os.path.isfile(path) else path

    click.echo(f"共发现 {len(targets)} 个任务，开始提取文字...", err=True)

    with click.progressbar(targets, label="OCR 进度") as bar:
        for target in bar:
            img_to_ocr = target
            temp_processed_path = None

            # 执行可选图像预处理
            if preprocessing:
                try:
                    from offline_ocr.utils.image_utils import safe_imwrite
                    # 先增强，再纠偏
                    processed_img = enhance_contrast(target)
                    # 写出到临时的临时文件，以便 PaddleOCR 载入
                    import tempfile
                    fd, temp_processed_path = tempfile.mkstemp(suffix=".png")
                    os.close(fd)
                    safe_imwrite(temp_processed_path, processed_img)

                    # 纠偏
                    rotated_img = deskew(temp_processed_path)
                    safe_imwrite(temp_processed_path, rotated_img)
                    img_to_ocr = temp_processed_path
                except Exception as e:
                    click.echo(f"\n图片预处理失败 {target}: {e}", err=True)

            try:
                results = ocr_engine.extract_text(img_to_ocr)

                # 输出文件名生成
                base_name = os.path.splitext(os.path.basename(target))[0]
                out_file_name = f"{base_name}_ocr.{format}"
                out_path = os.path.join(output_dir, out_file_name)

                if format == "txt":
                    save_text(results, out_path)
                elif format == "json":
                    save_json(results, out_path)
                elif format == "md":
                    save_markdown(results, out_path)
                elif format == "csv":
                    save_csv(results, out_path)

            except Exception as e:
                click.echo(f"\n文字提取失败 {target}: {e}", err=True)
            finally:
                if temp_processed_path and os.path.exists(temp_processed_path):
                    try:
                        os.remove(temp_processed_path)
                    except:
                        pass

    click.echo(f"提取完成！结果保存在: {os.path.abspath(output_dir)}", err=True)
    if temp_dir:
        temp_dir.cleanup()

if __name__ == "__main__":
    main()
