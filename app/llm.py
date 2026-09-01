"""调用 OpenAI 兼容接口的免费大模型（Ollama / SiliconFlow / GLM / DeepSeek / 自定义）。"""
import requests


def chat(cfg, messages, temperature=None, max_tokens=None, timeout=600):
    """调用 chat/completions 接口。

    :param cfg: 配置字典，至少包含 base_url / model / api_key
    :param messages: [{"role": "system"|"user"|"assistant", "content": str}, ...]
    :return: 模型返回的文本
    :raises RuntimeError: 配置缺失或调用失败
    """
    base = (cfg.get("base_url") or "").strip().rstrip("/")
    model = (cfg.get("model") or "").strip()
    api_key = (cfg.get("api_key") or "").strip()

    if not base:
        raise RuntimeError("未配置 API 地址 base_url，请在「设置」中填写。")
    if not model:
        raise RuntimeError("未配置模型名称 model，请在「设置」中填写。")

    url = base + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key

    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature if temperature is not None
                             else cfg.get("temperature", 0.7)),
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = int(max_tokens)

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.exceptions.RequestException as e:
        raise RuntimeError("连接 API 失败：" + str(e))

    if resp.status_code != 200:
        raise RuntimeError("API 返回错误 %s：%s" % (resp.status_code, resp.text[:400]))

    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError("无法解析 API 返回内容：" + resp.text[:400])