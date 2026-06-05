"""
Mac mini LLM 微服务
- 包装 mlx_lm (Apple Silicon Metal 加速)
- 端点:
  - GET  /health        健康检查
  - GET  /info          模型信息
  - POST /v1/chat       OpenAI 兼容 chat completion
  - POST /v1/generate   原始 prompt 续写
- 默认端口 8001, 绑定 0.0.0.0 (供 Tailscale 私网访问)
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from typing import Any

from flask import Flask, jsonify, request

log = logging.getLogger("llm_service")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)

DEFAULT_MODEL_DIR = os.path.expanduser("~/Models/Qwen3-4B-Thinking-2507-MLX-4bit")
DEFAULT_PORT = 8001
DEFAULT_HOST = "0.0.0.0"

# 推理默认参数
MAX_TOKENS = 1024
TEMP = 0.6
TOP_P = 0.95

app = Flask(__name__)
_model = None
_tokenizer = None
_model_dir: str = ""
_load_ms: int = 0


def load_model(model_dir: str) -> None:
    global _model, _tokenizer, _model_dir, _load_ms
    t0 = time.time()
    log.info("加载 mlx_lm 模型: %s", model_dir)
    from mlx_lm import load as mlx_load  # type: ignore
    _model, _tokenizer = mlx_load(model_dir)
    _model_dir = model_dir
    _load_ms = int((time.time() - t0) * 1000)
    log.info("模型加载完成, 耗时 %d ms", _load_ms)


def generate_text(prompt: str, max_tokens: int = MAX_TOKENS,
                  temp: float = TEMP, top_p: float = TOP_P) -> tuple[str, int]:
    """返回 (生成文本, 耗时 ms)"""
    from mlx_lm import generate as mlx_generate  # type: ignore
    t0 = time.time()
    text = mlx_generate(
        _model, _tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        temp=temp,
        top_p=top_p,
        verbose=False,
    )
    return text, int((time.time() - t0) * 1000)


def chat_to_prompt(messages: list[dict]) -> str:
    """把 OpenAI 风格 messages 转成 Qwen3 chat template."""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            parts.append(f"<|im_start|>system\n{content}<|im_end|>")
        elif role == "user":
            parts.append(f"<|im_start|>user\n{content}<|im_end|>")
        elif role == "assistant":
            parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
    parts.append("<|im_start|>assistant\n")
    return "\n".join(parts)


# ==================== 路由 ====================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": _model is not None,
        "model_dir": _model_dir,
        "load_ms": _load_ms,
    })


@app.route("/info")
def info():
    return jsonify({
        "model_dir": _model_dir,
        "backend": "mlx",
        "max_tokens": MAX_TOKENS,
        "temp": TEMP,
        "top_p": TOP_P,
    })


@app.route("/v1/chat", methods=["POST"])
def chat():
    if _model is None:
        return jsonify({"error": "model not loaded"}), 503
    data: dict[str, Any] = request.get_json(silent=True) or {}
    messages = data.get("messages")
    if not messages:
        return jsonify({"error": "missing 'messages' (list of {role,content})"}), 400
    max_tokens = int(data.get("max_tokens", MAX_TOKENS))
    temp = float(data.get("temperature", data.get("temp", TEMP)))
    top_p = float(data.get("top_p", TOP_P))

    prompt = chat_to_prompt(messages)
    text, ms = generate_text(prompt, max_tokens=max_tokens, temp=temp, top_p=top_p)
    return jsonify({
        "text": text,
        "content": text,
        "prompt_tokens": len(_tokenizer.encode(prompt)) if _tokenizer else 0,
        "completion_tokens": len(_tokenizer.encode(text)) if _tokenizer else 0,
        "elapsed_ms": ms,
    })


@app.route("/v1/generate", methods=["POST"])
def generate():
    if _model is None:
        return jsonify({"error": "model not loaded"}), 503
    data: dict[str, Any] = request.get_json(silent=True) or {}
    prompt = data.get("prompt")
    if not prompt:
        return jsonify({"error": "missing 'prompt'"}), 400
    max_tokens = int(data.get("max_tokens", MAX_TOKENS))
    temp = float(data.get("temperature", data.get("temp", TEMP)))
    top_p = float(data.get("top_p", TOP_P))

    text, ms = generate_text(prompt, max_tokens=max_tokens, temp=temp, top_p=top_p)
    return jsonify({
        "text": text,
        "prompt_tokens": len(_tokenizer.encode(prompt)) if _tokenizer else 0,
        "completion_tokens": len(_tokenizer.encode(text)) if _tokenizer else 0,
        "elapsed_ms": ms,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL_DIR", DEFAULT_MODEL_DIR))
    parser.add_argument("--port", type=int, default=int(os.environ.get("LLM_PORT", DEFAULT_PORT)))
    parser.add_argument("--host", default=os.environ.get("LLM_HOST", DEFAULT_HOST))
    args = parser.parse_args()

    if not os.path.isdir(args.model):
        log.error("模型目录不存在: %s", args.model)
        log.error("请先运行 download_models.sh 下载")
        return

    load_model(args.model)

    log.info("启动 HTTP 服务: http://%s:%d", args.host, args.port)
    log.info("  GET  /health")
    log.info("  GET  /info")
    log.info("  POST /v1/chat     {messages:[...], max_tokens, temperature, top_p}")
    log.info("  POST /v1/generate {prompt, max_tokens, temperature, top_p}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
