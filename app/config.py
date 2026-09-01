"""大模型与运行配置管理。

配置支持三处来源（优先级从高到低）：
1. 网页「设置」界面保存到 data/config.json
2. 环境变量 OFFICE_AI_BASE_URL / OFFICE_AI_MODEL / OFFICE_AI_API_KEY
3. 默认值
"""
import json
import os
from pathlib import Path

from .auth import hash_password, new_salt

DATA_DIR = Path(os.environ.get("OFFICE_AI_DATA_DIR", "data"))
CONFIG_FILE = DATA_DIR / "config.json"

# 内置的免费/低价大模型预设
PROVIDERS = [
    {
        "name": "本地 Ollama（免费，需自部署）",
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "api_key": "ollama",
        "need_key": False,
        "hint": "需要在服务器上安装并运行 Ollama（ollama run qwen2.5:7b），应用会自动调用本机接口。",
    },
    {
        "name": "硅基流动 SiliconFlow（免费额度）",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "api_key": "",
        "need_key": True,
        "hint": "到 https://siliconflow.cn 注册获取 API Key（新用户有免费额度）。",
    },
    {
        "name": "智谱 GLM-4-Flash（免费额度）",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "api_key": "",
        "need_key": True,
        "hint": "到 https://open.bigmodel.cn 注册获取 API Key，glm-4-flash 模型免费。",
    },
    {
        "name": "DeepSeek（低价，非免费）",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key": "",
        "need_key": True,
        "hint": "到 https://platform.deepseek.com 获取 API Key 并充值。",
    },
    {
        "name": "自定义 OpenAI 兼容接口",
        "base_url": "",
        "model": "",
        "api_key": "",
        "need_key": True,
        "hint": "任意兼容 OpenAI 的接口：填写 base_url（含 /v1）、model 名称、API Key。",
    },
]


def _default():
    p0 = PROVIDERS[0]
    return {
        "provider": 0,
        "base_url": p0["base_url"],
        "model": p0["model"],
        "api_key": os.environ.get("OFFICE_AI_API_KEY", p0["api_key"]),
        "temperature": 0.7,
        "max_tokens": 4096,
        "system_prompt": "你是 office_ai 助手，一个专业、准确、简洁的自动办公助理。",
        # 登录鉴权（默认开启，初始密码 admin123）
        "auth_enabled": True,
        "auth_salt": "",
        "auth_password_hash": "",
    }


def load_config():
    """加载配置（网页设置优先，其次环境变量，最后默认值）。"""
    cfg = _default()
    cfg["base_url"] = os.environ.get("OFFICE_AI_BASE_URL", cfg["base_url"])
    cfg["model"] = os.environ.get("OFFICE_AI_MODEL", cfg["model"])
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update(data)
    except Exception:
        pass
    _ensure_auth(cfg)
    return cfg


def _ensure_auth(cfg):
    """保证鉴权相关字段存在；首次启动生成盐并设置默认密码 admin123。"""
    if not cfg.get("auth_salt"):
        cfg["auth_salt"] = new_salt()
        cfg["auth_password_hash"] = hash_password("admin123", cfg["auth_salt"])
        try:
            save_config(cfg)
        except Exception:
            pass


def save_config(cfg):
    """保存网页配置到 data/config.json。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    keys = ("provider", "base_url", "model", "api_key",
            "temperature", "max_tokens", "system_prompt",
            "auth_enabled", "auth_salt", "auth_password_hash")
    safe = {k: cfg.get(k) for k in keys if k in cfg}
    CONFIG_FILE.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")


def masked(cfg):
    """返回隐藏 api_key 的配置（用于接口回显）。"""
    c = dict(cfg)
    if c.get("api_key"):
        c["api_key"] = "********"
    else:
        c["api_key"] = ""
    c.pop("auth_salt", None)
    c.pop("auth_password_hash", None)
    return c