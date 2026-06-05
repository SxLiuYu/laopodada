"""
Mac mini FashionCLIP 微服务
- 包装 Marqo/marqo-fashionCLIP (transformers, MPS 加速)
- 端点:
  - GET  /health
  - GET  /info
  - POST /v1/encode   multipart: image=<file>  或 JSON: image_url=<url>
- 默认端口 8002, 绑定 0.0.0.0
"""
from __future__ import annotations

import argparse
import io
import logging
import os
import time
from typing import Any

from flask import Flask, jsonify, request
from PIL import Image

log = logging.getLogger("visual_service")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)

DEFAULT_MODEL = "Marqo/marqo-fashionCLIP"
DEFAULT_PORT = 8002
DEFAULT_HOST = "0.0.0.0"
EMBED_DIM = 512

app = Flask(__name__)
_model = None
_processor = None
_device = "cpu"
_model_id: str = ""
_load_ms: int = 0


def load_model(model_id: str) -> None:
    global _model, _processor, _device, _model_id, _load_ms
    t0 = time.time()
    log.info("加载 FashionCLIP: %s", model_id)
    import torch
    from transformers import CLIPModel, CLIPProcessor

    if torch.backends.mps.is_available():
        _device = "mps"
    elif torch.cuda.is_available():
        _device = "cuda"
    else:
        _device = "cpu"
    log.info("推理设备: %s", _device)

    _model = CLIPModel.from_pretrained(model_id).to(_device).eval()
    _processor = CLIPProcessor.from_pretrained(model_id)
    _model_id = model_id
    _load_ms = int((time.time() - t0) * 1000)
    log.info("FashionCLIP 加载完成, 耗时 %d ms", _load_ms)


def encode_image(img: Image.Image) -> list[float]:
    import torch
    inputs = _processor(images=img, return_tensors="pt").to(_device)
    with torch.no_grad():
        feat = _model.get_image_features(**inputs)
    # L2 normalize (与云端 cosine 兼容)
    feat = feat / feat.norm(dim=-1, keepdim=True).clamp(min=1e-9)
    return feat[0].cpu().float().tolist()


# ==================== 路由 ====================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": _model is not None,
        "model_id": _model_id,
        "device": _device,
        "load_ms": _load_ms,
        "embed_dim": EMBED_DIM,
    })


@app.route("/info")
def info():
    return jsonify({
        "model_id": _model_id,
        "device": _device,
        "embed_dim": EMBED_DIM,
    })


@app.route("/v1/encode", methods=["POST"])
def encode():
    if _model is None:
        return jsonify({"error": "model not loaded"}), 503

    img: Image.Image | None = None
    if "image" in request.files:
        f = request.files["image"]
        img = Image.open(io.BytesIO(f.read())).convert("RGB")
    else:
        data: dict[str, Any] = request.get_json(silent=True) or {}
        url = data.get("image_url")
        b64 = data.get("image_b64")
        if url:
            import requests as _req
            r = _req.get(url, timeout=15)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
        elif b64:
            import base64
            img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

    if img is None:
        return jsonify({
            "error": "missing image: send multipart 'image' or JSON {image_url|image_b64}"
        }), 400

    t0 = time.time()
    vec = encode_image(img)
    ms = int((time.time() - t0) * 1000)
    return jsonify({
        "embedding": vec,
        "dim": len(vec),
        "elapsed_ms": ms,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("FASHION_MODEL", DEFAULT_MODEL))
    parser.add_argument("--port", type=int, default=int(os.environ.get("VISUAL_PORT", DEFAULT_PORT)))
    parser.add_argument("--host", default=os.environ.get("VISUAL_HOST", DEFAULT_HOST))
    args = parser.parse_args()

    load_model(args.model)

    log.info("启动 HTTP 服务: http://%s:%d", args.host, args.port)
    log.info("  GET  /health")
    log.info("  GET  /info")
    log.info("  POST /v1/encode   (multipart 'image' or JSON 'image_url'/'image_b64')")
    app.run(host=args.host, port=args.port, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
