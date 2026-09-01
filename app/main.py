"""Office AI 自动化办公助手 - FastAPI 应用与接口。"""
import io
import json
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import (auth, batch_ops, config, excel_ops, llm,
               pdf_ops, ppt_ops, template_ops, word_ops)

BASE = Path(__file__).resolve().parent

app = FastAPI(
    title="Office AI 自动化办公助手",
    description="处理 Word / Excel / PPT 的自动化办公 Web 应用，内置免费大模型。",
    version="1.0.0",
)


# 无需登录即可访问的公开接口
PUBLIC_PATHS = {"/api/login", "/api/logout", "/api/me"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """除登录相关接口外，所有 /api 接口都需要登录。"""
    if request.url.path.startswith("/api") and request.url.path not in PUBLIC_PATHS:
        cfg = config.load_config()
        if cfg.get("auth_enabled", True):
            token = request.cookies.get("office_ai_token", "")
            if not auth.verify_token(token, cfg):
                return JSONResponse(status_code=401,
                                    content={"error": "未登录或会话已过期，请先登录。"})
    return await call_next(request)


def _zip_bytes(pairs):
    """把 [(文件名, bytes), ...] 打包为 zip 字节。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in pairs:
            z.writestr(name, data)
    return buf.getvalue()


def _download(buf, filename, media_type):
    return StreamingResponse(
        io.BytesIO(buf),
        media_type=media_type,
        headers={"Content-Disposition": "attachment; filename*=UTF-8''%s" % quote(filename)},
    )


def _err(e):
    return JSONResponse(status_code=400, content={"error": str(e)})


# ---------------------------------------------------------------- 登录鉴权
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    cfg = config.load_config()
    if auth.verify_password(data.get("password", ""), cfg):
        resp = JSONResponse({"ok": True})
        resp.set_cookie("office_ai_token", auth.make_token(cfg),
                        httponly=True, max_age=2592000, samesite="lax")
        return resp
    return JSONResponse(status_code=401, content={"error": "密码错误"})


@app.post("/api/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("office_ai_token")
    return resp


@app.get("/api/me")
async def me(request: Request):
    cfg = config.load_config()
    if cfg.get("auth_enabled", True):
        authed = auth.verify_token(request.cookies.get("office_ai_token", ""), cfg)
    else:
        authed = True
    return {"authed": authed, "auth_enabled": bool(cfg.get("auth_enabled", True))}


@app.post("/api/password")
async def change_password(request: Request):
    data = await request.json()
    cfg = config.load_config()
    if not auth.verify_password(data.get("old", ""), cfg):
        return JSONResponse(status_code=401, content={"error": "原密码错误"})
    new_pwd = str(data.get("new", ""))
    if len(new_pwd) < 6:
        return _err("新密码至少 6 位")
    cfg["auth_password_hash"] = auth.hash_password(
        new_pwd, cfg.get("auth_salt", ""))
    config.save_config(cfg)
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index():
    return (BASE / "static" / "index.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------- 配置相关
@app.get("/api/settings")
def get_settings():
    cfg = config.load_config()
    cfg["providers"] = config.PROVIDERS
    return config.masked(cfg)


@app.post("/api/settings")
async def save_settings(request: Request):
    data = await request.json()
    cfg = config.load_config()
    for key in ("provider", "base_url", "model", "api_key",
                "temperature", "max_tokens", "system_prompt"):
        if key in data:
            cfg[key] = data[key]
    config.save_config(cfg)
    return {"ok": True}


@app.post("/api/test")
async def test_connection(request: Request):
    data = await request.json()
    cfg = dict(config.load_config())
    for key in ("base_url", "model", "api_key", "temperature"):
        if key in data:
            cfg[key] = data[key]
    try:
        reply = llm.chat(cfg, [{"role": "user", "content": "请只回复四个字：连接成功"}],
                         max_tokens=32, timeout=60)
        return {"ok": True, "reply": reply}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    cfg = config.load_config()
    try:
        reply = llm.chat(cfg, data.get("messages", []),
                         max_tokens=int(cfg.get("max_tokens", 4096)), timeout=900)
        provider_name = config.PROVIDERS[int(cfg.get("provider", 0))]["name"]
        return {"reply": reply, "provider": provider_name, "model": cfg.get("model")}
    except Exception as e:
        return _err(e)


# ---------------------------------------------------------------- Word
@app.post("/api/word/generate")
async def word_generate(request: Request):
    data = await request.json()
    cfg = config.load_config()
    try:
        buf, content = word_ops.generate_document(
            cfg, data.get("topic", ""), data.get("extra", ""))
        if data.get("as_pdf"):
            pdf = pdf_ops.convert_to_pdf(buf, ".docx")
            name = (data.get("topic") or "文档").strip() or "文档"
            return _download(_zip_bytes([(name + ".docx", buf), (name + ".pdf", pdf)]),
                             "AI文档.zip", "application/zip")
        return _download(buf, "ai_generated.docx",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        return _err(e)


@app.post("/api/word/summarize")
async def word_summarize(file: UploadFile = File(...)):
    content = await file.read()
    cfg = config.load_config()
    try:
        return {"summary": word_ops.summarize_document(cfg, content)}
    except Exception as e:
        return _err(e)


@app.post("/api/word/translate")
async def word_translate(file: UploadFile = File(...), target: str = Form("英语")):
    content = await file.read()
    cfg = config.load_config()
    try:
        buf = word_ops.translate_document(cfg, content, target)
        return _download(buf, "translated.docx",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        return _err(e)


# ---------------------------------------------------------------- PDF 转换
@app.post("/api/pdf/convert")
async def pdf_convert(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "file.docx"
    try:
        buf = pdf_ops.convert_to_pdf(content, Path(filename).suffix.lower())
        return _download(buf, Path(filename).stem + ".pdf", "application/pdf")
    except Exception as e:
        return _err(e)


# ---------------------------------------------------------------- Excel
@app.post("/api/excel/info")
async def excel_info(file: UploadFile = File(...)):
    content = await file.read()
    try:
        _, sheets = excel_ops.load_sheet_info(content)
        return {"sheets": sheets}
    except Exception as e:
        return _err(e)


@app.post("/api/excel/analyze")
async def excel_analyze(file: UploadFile = File(...), extra: str = Form("")):
    content = await file.read()
    cfg = config.load_config()
    try:
        _, sheets = excel_ops.load_sheet_info(content)
        analysis = excel_ops.analyze_sheet(cfg, content, extra)
        return {"analysis": analysis, "sheets": sheets}
    except Exception as e:
        return _err(e)


@app.post("/api/excel/report")
async def excel_report(file: UploadFile = File(...), analysis: str = Form("")):
    content = await file.read()
    try:
        buf = excel_ops.add_analysis_sheet(content, analysis)
        return _download(buf, "with_ai_report.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return _err(e)


@app.post("/api/excel/generate-rows")
async def excel_generate_rows(file: UploadFile = File(...),
                              sheet: str = Form(""),
                              n: int = Form(10),
                              extra: str = Form("")):
    content = await file.read()
    cfg = config.load_config()
    try:
        buf, start, wrote = excel_ops.generate_rows(cfg, content, sheet, n, extra)
        return _download(buf, "generated_data.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return _err(e)


@app.post("/api/excel/chart")
async def excel_chart(file: UploadFile = File(...),
                      sheet: str = Form(""),
                      chart_type: str = Form("bar")):
    content = await file.read()
    try:
        buf = excel_ops.add_chart(content, sheet, chart_type)
        return _download(buf, "with_chart.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return _err(e)


# ---------------------------------------------------------------- PPT
@app.post("/api/ppt/generate")
async def ppt_generate(request: Request):
    data = await request.json()
    cfg = config.load_config()
    try:
        buf, content = ppt_ops.generate_ppt(
            cfg, data.get("topic", ""), int(data.get("slides", 6)), data.get("extra", ""))
        if data.get("as_pdf"):
            pdf = pdf_ops.convert_to_pdf(buf, ".pptx")
            name = (data.get("topic") or "演示文稿").strip() or "演示文稿"
            return _download(_zip_bytes([(name + ".pptx", buf), (name + ".pdf", pdf)]),
                             "AI演示文稿.zip", "application/zip")
        return _download(buf, "ai_generated.pptx",
                         "application/vnd.openxmlformats-officedocument.presentationml.presentation")
    except Exception as e:
        return _err(e)


@app.post("/api/ppt/summarize")
async def ppt_summarize(file: UploadFile = File(...)):
    content = await file.read()
    cfg = config.load_config()
    try:
        return {"summary": ppt_ops.summarize_presentation(cfg, content)}
    except Exception as e:
        return _err(e)


# ---------------------------------------------------------------- Word 模板套用
@app.post("/api/template/fields")
async def template_fields(file: UploadFile = File(...)):
    content = await file.read()
    try:
        return {"fields": template_ops.extract_placeholders(content)}
    except Exception as e:
        return _err(e)


@app.post("/api/template/ai-suggest")
async def template_ai_suggest(file: UploadFile = File(...), context: str = Form("")):
    content = await file.read()
    cfg = config.load_config()
    try:
        return {"values": template_ops.ai_fill(cfg, content, context)}
    except Exception as e:
        return _err(e)


@app.post("/api/template/fill")
async def template_fill(file: UploadFile = File(...), values: str = Form("{}")):
    content = await file.read()
    try:
        vals = json.loads(values or "{}")
        buf = template_ops.fill_template(content, vals)
        name = "filled_" + (file.filename or "模板.docx")
        return _download(buf, name,
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        return _err(e)


# ---------------------------------------------------------------- 批量处理
@app.post("/api/batch")
async def batch_process(files: list[UploadFile] = File(...),
                        op: str = Form("word_summary"),
                        target: str = Form("英语")):
    cfg = config.load_config()
    try:
        payload = []
        for f in files:
            content = await f.read()
            payload.append((f.filename or "file.docx", content))
        zip_bytes = batch_ops.run_batch(cfg, op, payload, target)
        return _download(zip_bytes, "batch_result.zip", "application/zip")
    except Exception as e:
        return _err(e)


# ---------------------------------------------------------------- 静态资源
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")