"""将 docx / pptx 转为 PDF：依赖服务器上安装的 LibreOffice。"""
import subprocess
import tempfile
from pathlib import Path
from shutil import which

SUPPORTED = {".docx", ".pptx"}


def convert_to_pdf(content: bytes, ext: str) -> bytes:
    """调用 LibreOffice headless 把 Office 文档转为 PDF，返回 PDF 字节。"""
    ext = (ext or "").lower()
    if ext not in SUPPORTED:
        raise RuntimeError("仅支持将 .docx / .pptx 转为 PDF。")
    binary = next((n for n in ("libreoffice", "soffice") if which(n)), None)
    if binary is None:
        raise RuntimeError(
            "服务器未安装 LibreOffice，无法转换 PDF。\n"
            "Debian/Ubuntu：apt-get install -y libreoffice-writer libreoffice-impress\n"
            "CentOS：yum install -y libreoffice"
        )
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / ("input" + ext)
        src.write_bytes(content)
        outdir = Path(td) / "out"
        outdir.mkdir()
        cmd = [binary, "--headless", "--convert-to", "pdf",
               "--outdir", str(outdir), str(src)]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=300)
        except subprocess.TimeoutExpired:
            raise RuntimeError("PDF 转换超时。")
        if proc.returncode != 0:
            msg = (proc.stderr or b"").decode("utf-8", errors="replace") or \
                  (proc.stdout or b"").decode("utf-8", errors="replace")
            raise RuntimeError("PDF 转换失败：" + msg[:300])
        pdf = outdir / "input.pdf"
        if not pdf.exists():
            raise RuntimeError("PDF 转换失败：未生成输出文件。")
        return pdf.read_bytes()