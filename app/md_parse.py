"""把 AI 输出的 Markdown 文本解析为结构化 block 列表，供 Word / PPT 生成使用。"""
import re

_TYPES = ("title", "h1", "h2", "h3", "para", "bullet", "numbered")


def parse_markdown(text):
    """解析 AI 返回的 Markdown 文本。

    :return: [{"type": "title"|"h1"|"h2"|"h3"|"para"|"bullet"|"numbered", "text": str}, ...]
    """
    blocks = []
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            continue

        # 标题：# / ## / ### ...
        if s.startswith("#"):
            m = re.match(r"^(#{1,6})\s+(.*)$", s)
            if m:
                level = len(m.group(1))
                blocks.append({"type": "h%d" % min(level, 3), "text": m.group(2).strip()})
            continue

        # 无序列表
        m = re.match(r"^[-*•◦]\s+(.*)$", s)
        if m:
            blocks.append({"type": "bullet", "text": m.group(1).strip()})
            continue

        # 有序列表
        m = re.match(r"^(\d{1,3})[.、．.)]\s+(.*)$", s)
        if m:
            blocks.append({"type": "numbered", "text": m.group(2).strip()})
            continue

        blocks.append({"type": "para", "text": s})
    return blocks