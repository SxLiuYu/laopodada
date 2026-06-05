"""
LLM 精排器
- Mac Apple Silicon: mlx_lm (Metal 加速)
- Linux/Windows: transformers (CPU 兼容, 自动选 bf16/fp16)
- 内存不足时模块置为不可用，不抛错
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from .device import (
    can_fit_llm,
    get_available_memory_mb,
    get_llm_dir,
    has_mlx,
)

log = logging.getLogger(__name__)

# 内存阈值：低于此值则拒绝加载
MIN_LLM_MEMORY_MB = 900


class OutfitReasoner:
    def __init__(self, model_dir: str | None = None, remote_url: str | None = None):
        self.model_dir = model_dir or get_llm_dir()
        # 远程模式: LLM_REMOTE_URL=http://host:port  (例: Tailscale 100.x IP:8001)
        self.remote_url = (remote_url or os.environ.get("LLM_REMOTE_URL", "")).rstrip("/")
        self._backend: Optional[str] = None
        self._model = None
        self._tokenizer = None
        self._loaded = False
        self._disabled_reason: str | None = None
        self._last_remote_check_ms: int = 0
        self._remote_healthy: bool = False

    # ---------- 状态 ----------

    @staticmethod
    def is_available() -> bool:
        """本地模型存在 OR 远程 URL 已配置"""
        if os.environ.get("LLM_REMOTE_URL"):
            return True
        from .device import get_llm_dir
        d = get_llm_dir()
        return os.path.isdir(d) and any(os.scandir(d))

    def is_ready(self) -> bool:
        if self.remote_url:
            return self._remote_healthy and self._disabled_reason is None
        return self._loaded and self._model is not None and self._disabled_reason is None

    def disabled_reason(self) -> str | None:
        return self._disabled_reason

    def model_exists(self) -> bool:
        return os.path.isdir(self.model_dir)

    def is_remote(self) -> bool:
        return bool(self.remote_url)

    def backend(self) -> str:
        if self.remote_url:
            return "remote" if self._remote_healthy else "remote(unreachable)"
        return self._backend or "none"

    # ---------- 加载 ----------

    def load(self) -> None:
        if self._loaded:
            return

        # 远程模式: 只做 health check, 不加载本地模型
        if self.remote_url:
            self._check_remote_health()
            self._loaded = True
            return

        # 内存检查
        avail = get_available_memory_mb()
        if avail is not None and avail < MIN_LLM_MEMORY_MB:
            self._disabled_reason = f"可用内存仅 {avail}MB, 不足以加载 LLM (需 ≥{MIN_LLM_MEMORY_MB}MB)"
            log.warning("LLM 自动禁用: %s", self._disabled_reason)
            return

        if not os.path.isdir(self.model_dir):
            self._disabled_reason = f"模型目录不存在: {self.model_dir}"
            log.warning("LLM 自动禁用: %s", self._disabled_reason)
            return

        # 检查模型权重
        has_weights = any(
            f.endswith((".safetensors", ".bin", ".gguf"))
            for f in os.listdir(self.model_dir)
        ) if os.path.isdir(self.model_dir) else False
        if not has_weights:
            self._disabled_reason = f"模型目录无权重文件: {self.model_dir}"
            log.warning("LLM 自动禁用: %s", self._disabled_reason)
            return

        try:
            if has_mlx():
                self._load_mlx()
            else:
                self._load_hf_fallback()
            self._loaded = True
        except MemoryError:
            self._disabled_reason = "加载 LLM 时 OOM (内存不足)"
            log.exception("LLM 加载 OOM")
        except Exception as e:
            self._disabled_reason = f"LLM 加载失败: {type(e).__name__}: {e}"
            log.exception("LLM 加载失败")

    def _check_remote_health(self, force: bool = False) -> None:
        """探活远程 LLM 服务. 每 60s 才重新查一次 (健康检查)"""
        import time as _t
        now = int(_t.time() * 1000)
        if not force and (now - self._last_remote_check_ms) < 60_000 and self._disabled_reason is None:
            return
        self._last_remote_check_ms = now
        try:
            import requests as _req
            r = _req.get(f"{self.remote_url}/health", timeout=5)
            r.raise_for_status()
            data = r.json()
            if data.get("model_loaded"):
                self._remote_healthy = True
                self._disabled_reason = None
                log.info("远程 LLM 健康: %s", self.remote_url)
            else:
                self._remote_healthy = False
                self._disabled_reason = f"远程 LLM 服务未加载模型: {self.remote_url}"
                log.warning(self._disabled_reason)
        except Exception as e:
            self._remote_healthy = False
            self._disabled_reason = f"远程 LLM 不可达 ({type(e).__name__}): {self.remote_url}"
            log.warning("远程 LLM 健康检查失败: %s", e)

    def _load_mlx(self) -> None:
        from mlx_lm import load
        log.info("加载 LLM (mlx_lm): %s", self.model_dir)
        self._model, self._tokenizer = load(self.model_dir)
        self._backend = "mlx"

    def _load_hf_fallback(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from .device import get_torch_device
        import torch
        device = get_torch_device()
        log.info("加载 LLM (transformers %s): %s", device, self.model_dir)
        # 选 dtype: 优先 bf16 (省内存), 不支持则 fp16
        dtype = torch.bfloat16 if device != "cpu" else torch.float32
        # CPU 优先用 float32 (更稳); 实际最省内存是量化, 但 bitsandbytes 需要 CUDA
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_dir, torch_dtype=dtype, low_cpu_mem_usage=True
        )
        if device != "cpu":
            self._model = self._model.to(device)
        self._model.eval()
        self._backend = "hf"
        self._device = device

    # ---------- 生成 ----------

    def _generate(self, prompt: str, max_tokens: int = 700, temperature: float = 0.3) -> str:
        if not self.is_ready():
            raise RuntimeError(f"LLM 不可用: {self._disabled_reason or 'not loaded'}")

        # 远程模式
        if self.remote_url:
            self._check_remote_health()
            if not self._remote_healthy:
                raise RuntimeError(self._disabled_reason or "远程 LLM 不可达")
            import requests as _req
            # 把 chat template 拼好的 prompt 转回 messages
            # (云端是 client 视角, 知道 system/user 的边界)
            sys_part, usr_part = self._unwrap_chat(prompt)
            r = _req.post(
                f"{self.remote_url}/v1/chat",
                json={
                    "messages": [
                        {"role": "system", "content": sys_part},
                        {"role": "user", "content": usr_part},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            return data.get("text") or data.get("content") or ""

        if self._backend == "mlx":
            from mlx_lm import generate as mlx_generate
            return mlx_generate(
                self._model, self._tokenizer,
                prompt=prompt, max_tokens=max_tokens, temp=temperature, verbose=False,
            )
        else:
            import torch
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
            with torch.no_grad():
                out = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=temperature > 0,
                    temperature=max(temperature, 0.01),
                    top_p=0.9,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
            new_ids = out[0][inputs.input_ids.shape[1]:]
            return self._tokenizer.decode(new_ids, skip_special_tokens=True)

    def rerank(self, weather: dict, occasion: str, candidates: list[dict]) -> dict:
        from .prompts import RERANK_SYSTEM, build_rerank_prompt

        if not candidates:
            return {"order": [], "reasons": {}}

        if not self.is_available():
            return self._fallback_order(candidates, "（未启用 AI 精排: 模型未下载）")

        if not self.is_ready():
            reason = self._disabled_reason or "未加载"
            return self._fallback_order(candidates, f"（AI 暂不可用: {reason}）")

        user_prompt = build_rerank_prompt(weather, occasion, candidates)
        prompt = self._wrap_chat(user_prompt, RERANK_SYSTEM)
        try:
            raw = self._generate(prompt, max_tokens=900, temperature=0.3)
            log.debug("LLM raw output: %s", raw[:500])
            return self._parse(raw, [c["id"] for c in candidates])
        except Exception as e:
            log.exception("LLM 精排失败: %s", e)
            return self._fallback_order(candidates, f"（AI 推理失败: {type(e).__name__}）")

    # ---------- 输出解析 ----------

    def _parse(self, raw: str, valid_ids: list[str]) -> dict:
        """从 LLM 输出中抽取 JSON。处理 Qwen3-Thinking 输出的 <think>...</think> 块。"""
        text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not m:
            raise ValueError(f"未找到 JSON: {raw[:200]}")
        block = m.group(0)
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*([}\]])", r"\1", block)
            data = json.loads(cleaned)

        order = data.get("order", [])
        reasons = data.get("reasons", {})

        order = [oid for oid in order if oid in valid_ids]
        for vid in valid_ids:
            if vid not in order:
                order.append(vid)
        reasons = {k: str(v)[:60] for k, v in reasons.items() if k in valid_ids}
        for vid in valid_ids:
            reasons.setdefault(vid, "暂未生成理由")

        return {"order": order, "reasons": reasons}

    # ---------- 工具 ----------

    def _wrap_chat(self, user: str, system: str) -> str:
        return (
            f"<|im_start|>system\n{system}<|im_end|>\n"
            f"<|im_start|>user\n{user}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def _unwrap_chat(self, prompt: str) -> tuple[str, str]:
        """把 _wrap_chat 拼好的 prompt 解回 (system, user). 远程模式用."""
        import re as _re
        m_sys = _re.search(r"<\|im_start\|>system\n(.*?)<\|im_end\|>", prompt, _re.DOTALL)
        m_usr = _re.search(r"<\|im_start\|>user\n(.*?)<\|im_end\|>", prompt, _re.DOTALL)
        return (m_sys.group(1) if m_sys else "", m_usr.group(1) if m_usr else "")

    def _fallback_order(self, candidates: list[dict], reason_suffix: str) -> dict:
        order = [c["id"] for c in sorted(candidates, key=lambda c: c.get("visual_score", 0), reverse=True)]
        reasons = {c["id"]: f"基于规则与视觉兼容性排序 {reason_suffix}".strip() for c in candidates}
        return {"order": order, "reasons": reasons}
