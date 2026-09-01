"""批量处理：对多个文件执行同一操作并打包为 zip。"""
import io
import zipfile
from pathlib import Path

from . import excel_ops, pdf_ops, ppt_ops, word_ops


def make_zip(items):
    """items: [(文件名, bytes), ...] → zip 字节。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in items:
            z.writestr(name, data)
    return buf.getvalue()


def run_batch(cfg, op, files, target="英语"):
    """按操作批量处理文件，返回 zip 字节。

    :param op: word_summary | word_translate | excel_analyze | ppt_summary | convert_pdf
    :param files: [(文件名, bytes), ...]
    """
    out = []
    errors = []
    for name, content in files:
        base = Path(name or "file").stem
        try:
            if op == "word_summary":
                out.append((base + "_摘要.txt",
                            word_ops.summarize_document(cfg, content).encode("utf-8")))
            elif op == "word_translate":
                out.append((base + "_翻译.docx",
                            word_ops.translate_document(cfg, content, target)))
            elif op == "excel_analyze":
                out.append((base + "_分析.txt",
                            excel_ops.analyze_sheet(cfg, content).encode("utf-8")))
            elif op == "ppt_summary":
                out.append((base + "_摘要.txt",
                            ppt_ops.summarize_presentation(cfg, content).encode("utf-8")))
            elif op == "convert_pdf":
                ext = Path(name or "file.docx").suffix.lower()
                out.append((base + ".pdf", pdf_ops.convert_to_pdf(content, ext)))
            else:
                raise RuntimeError("未知操作：" + str(op))
        except Exception as e:
            errors.append("%s：%s" % (name or "未知文件", e))
    if errors:
        out.insert(0, ("_错误记录.txt", ("\n".join(errors)).encode("utf-8")))
    if not out:
        raise RuntimeError("没有可下载的文件，请检查输入。")
    return make_zip(out)