"""单用户登录鉴权：密码哈希 + 会话令牌。"""
import hashlib
import hmac
import secrets


def new_salt():
    """生成随机盐值。"""
    return secrets.token_hex(16)


def hash_password(password, salt):
    """计算密码哈希，返回十六进制字符串。"""
    return hashlib.sha256(("%s:%s" % (salt, password)).encode("utf-8")).hexdigest()


def make_token(cfg):
    """根据密码哈希和盐值生成稳定的登录令牌（密码不变则令牌不变）。"""
    salt = cfg.get("auth_salt", "") or ""
    pw_hash = cfg.get("auth_password_hash", "") or ""
    return hashlib.sha256(("%s:token:%s" % (salt, pw_hash)).encode("utf-8")).hexdigest()


def verify_password(password, cfg):
    """校验密码（常量时间比较）。鉴权关闭时直接通过。"""
    if not cfg.get("auth_enabled", True):
        return True
    salt = cfg.get("auth_salt", "") or ""
    expected = cfg.get("auth_password_hash", "") or ""
    if not expected:
        return False
    return hmac.compare_digest(hash_password(password, salt), expected)


def verify_token(token, cfg):
    """校验登录令牌。鉴权关闭时直接通过。"""
    if not cfg.get("auth_enabled", True):
        return True
    expected = make_token(cfg)
    return bool(token) and hmac.compare_digest(token, expected)