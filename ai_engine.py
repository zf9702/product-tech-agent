"""
AI 模型接口 — 可配置后端
支持 OpenAI 兼容 API（MiMo/DeepSeek/通义千问等）
"""
import json
import os
from pathlib import Path
from config import BASE_DIR

# AI 配置文件
AI_CONFIG_FILE = BASE_DIR / "ai_config.json"

DEFAULT_AI_CONFIG = {
    "provider": "",          # deepseek / openai / mimo / custom
    "api_base": "",          # API 地址
    "api_key": "",           # API 密钥
    "model": "",             # 模型名称
    "max_tokens": 4096,
    "temperature": 0.3,
    "enabled": False,
}


def load_ai_config() -> dict:
    if AI_CONFIG_FILE.exists():
        try:
            return json.loads(AI_CONFIG_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return DEFAULT_AI_CONFIG.copy()


def save_ai_config(config: dict):
    AI_CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def is_ai_available() -> bool:
    config = load_ai_config()
    return config.get("enabled", False) and bool(config.get("api_key"))


def call_ai(system_prompt: str, user_message: str, context: str = "") -> str:
    """
    调用 AI 模型
    支持 OpenAI 兼容 API 格式
    """
    config = load_ai_config()
    if not config.get("enabled") or not config.get("api_key"):
        return "[AI 未配置] 请在系统管理 > AI 设置 中配置模型接口"

    api_base = config["api_base"].rstrip("/")
    api_key = config["api_key"]
    model = config["model"]

    # 构建消息
    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "user", "content": f"以下是参考文档内容：\n\n{context}"})
        messages.append({"role": "assistant", "content": "好的，我已经阅读了文档内容，请提问。"})
    messages.append({"role": "user", "content": user_message})

    # 调用 API
    import urllib.request
    import urllib.error

    url = f"{api_base}/v1/chat/completions"
    # 处理不同的 API base URL 格式
    if "/v1" in api_base:
        url = f"{api_base}/chat/completions"
    elif api_base.endswith("/v1"):
        url = f"{api_base}/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": config.get("max_tokens", 4096),
        "temperature": config.get("temperature", 0.3),
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            result = json.loads(raw.decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        raw = e.read()
        body = raw.decode("utf-8", errors="ignore")
        return f"[AI 调用失败] HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return f"[AI 调用失败] {str(e)}"


# ─── 预设 Prompt ──────────────────────────────────

QA_SYSTEM_PROMPT = """你是一个航空设备产品技术资料管理系统的 AI 助手。
你的职责是根据用户上传的技术文档内容，回答关于产品技术参数、测试结果、规格要求等问题。

回答要求：
1. 严格基于文档内容回答，不要编造信息
2. 如果文档中没有相关信息，明确说明
3. 引用具体数据时标注来源文档
4. 使用专业但易懂的语言
5. 涉及技术参数时给出具体数值"""


COMPLIANCE_SYSTEM_PROMPT = """你是一个航空设备投标文件符合性检查专家。
你的任务是将投标文件内容与技术标准/招标要求逐条比对，输出符合性检查结果。

输出格式要求（严格按此格式）：
对每一条要求，输出：
  序号 | 要求内容 | 投标响应 | 符合性判定 | 说明
  ---|---|---|---|---
  1 | xxx | xxx | 符合/不符合/部分符合 | 说明

最后给出总结：
- 总条款数
- 符合数
- 不符合数
- 部分符合数
- 总体判定（通过/不通过）"""


def ask_question(question: str, context: str = "") -> str:
    """知识问答"""
    return call_ai(QA_SYSTEM_PROMPT, question, context)


def check_compliance(bid_content: str, standard_content: str) -> str:
    """符合性检查"""
    user_msg = f"""请对以下投标文件内容进行符合性检查。

=== 技术标准/招标要求 ===
{standard_content}

=== 投标文件内容 ===
{bid_content}

请逐条比对，输出符合性检查结果。"""
    return call_ai(COMPLIANCE_SYSTEM_PROMPT, user_msg)
