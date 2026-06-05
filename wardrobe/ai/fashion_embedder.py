"""
FashionCLIP 视觉编码器
- 本地模式: 加载 Marqo/marqo-fashionCLIP, 用 transformers + torch
- 远程模式: 通过 HTTP 调用家里 Mac mini 上的视觉服务（需配 FASHION_CLIP_REMOTE_URL）
- 内存不足时自动降级为"无视觉"
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from .device import (
    can_fit_visual,
    get_available_memory_mb,
    get_fashion_clip_dir,
    get_torch_device,
)

log = logging.getLogger(__name__)

EMB_DIM = 512
EMB_FILE = "embeddings.npy"
IDX_FILE = "emb_index.json"

# 内存阈值：低于此值拒绝加载（避免 OOM）
MIN_VISUAL_MEMORY_MB = 700


class FashionEmbedder:
    """
    服装视觉编码器。

    模式:
    - 本地 (默认): 加载本地 Marqo-FashionCLIP
    - 远程: 通过 HTTP 调用外部视觉服务 (FASHION_CLIP_REMOTE_URL)
    """

    def __init__(self, data_dir: str | os.PathLike = "data", model_dir: str | None = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir = model_dir or get_fashion_clip_dir()
        self.device = get_torch_device()
        self.model = None
        self.processor = None
        self._loaded = False
        self._disabled_reason: str | None = None
        self._is_remote = False
        self._remote_url = os.environ.get("FASHION_CLIP_REMOTE_URL", "").rstrip("/")
        self._emb_array: np.ndarray | None = None
        self._id_to_idx: dict[str, int] = {}
        self._idx_to_id: list[str] = []

    # ---------- 状态 ----------

    def is_ready(self) -> bool:
        return self._loaded and (self.model is not None or self._is_remote) and self._disabled_reason is None

    def is_remote(self) -> bool:
        return self._is_remote

    def model_exists(self) -> bool:
        if self._remote_url:
            return True  # 远程模式：假设服务在线，加载时再验证
        return Path(self.model_dir).exists() and any(Path(self.model_dir).iterdir())

    def disabled_reason(self) -> str | None:
        return self._disabled_reason

    def load(self) -> None:
        if self._loaded:
            return
        # 内存检查 (本地模式才需要)
        if not self._remote_url:
            avail = get_available_memory_mb()
            if avail is not None and avail < MIN_VISUAL_MEMORY_MB:
                self._disabled_reason = f"可用内存仅 {avail}MB, 不足以加载 FashionCLIP (需 ≥{MIN_VISUAL_MEMORY_MB}MB)"
                log.warning("FashionCLIP 自动禁用: %s", self._disabled_reason)
                return

        if self._remote_url:
            self._load_remote()
        else:
            self._load_local()
        self._loaded = True
        self._load_cache()

    def _load_local(self) -> None:
        import torch
        from transformers import AutoModel, AutoProcessor
        if not self.model_exists():
            raise FileNotFoundError(
                f"FashionCLIP 模型未找到: {self.model_dir}\n"
                f"先运行 download_models.sh 下载, 或设 FASHION_CLIP_DIR / FASHION_CLIP_REMOTE_URL"
            )
        log.info("加载 FashionCLIP: %s → device=%s", self.model_dir, self.device)
        try:
            self.model = AutoModel.from_pretrained(
                self.model_dir, trust_remote_code=True
            ).to(self.device).eval()
            self.processor = AutoProcessor.from_pretrained(
                self.model_dir, trust_remote_code=True
            )
        except MemoryError:
            self._disabled_reason = "加载 FashionCLIP OOM (内存不足)"
            log.exception(self._disabled_reason)
            self.model = None
            self.processor = None
            raise

    def _load_remote(self) -> None:
        """远程模式: 仅检查 URL 可达性, 不实际加载模型。"""
        import requests
        log.info("使用远程视觉服务: %s", self._remote_url)
        try:
            r = requests.get(f"{self._remote_url}/health", timeout=5)
            r.raise_for_status()
            self._is_remote = True
        except Exception as e:
            self._disabled_reason = f"远程视觉服务不可达 ({self._remote_url}): {e}"
            log.warning(self._disabled_reason)
            raise

    # ---------- 持久化缓存 ----------

    def _cache_paths(self) -> tuple[Path, Path]:
        return self.data_dir / EMB_FILE, self.data_dir / IDX_FILE

    def _load_cache(self) -> None:
        emb_p, idx_p = self._cache_paths()
        if emb_p.exists() and idx_p.exists():
            self._emb_array = np.load(emb_p)
            with open(idx_p, "r", encoding="utf-8") as f:
                self._id_to_idx = json.load(f)
            self._idx_to_id = [None] * len(self._id_to_idx)
            for k, v in self._id_to_idx.items():
                if 0 <= v < len(self._idx_to_id):
                    self._idx_to_id[v] = k
        else:
            self._emb_array = np.zeros((0, EMB_DIM), dtype=np.float32)
            self._id_to_idx = {}
            self._idx_to_id = []

    def _save_cache(self) -> None:
        emb_p, idx_p = self._cache_paths()
        np.save(emb_p, self._emb_array)
        with open(idx_p, "w", encoding="utf-8") as f:
            json.dump(self._id_to_idx, f, ensure_ascii=False, indent=2)

    # ---------- 编码 ----------

    def encode_image(self, image_path: str | os.PathLike) -> np.ndarray:
        """对单张图片生成 512-d 归一化向量。"""
        if not self.is_ready():
            self.load()
        if self._is_remote:
            return self._encode_remote(image_path)
        return self._encode_local(image_path)

    def _encode_local(self, image_path) -> np.ndarray:
        import torch
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        with torch.no_grad():
            inputs = self.processor(images=img, return_tensors="pt").to(self.device)
            feat = self.model.get_image_features(**inputs)
            feat = feat / feat.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        return feat.cpu().numpy().flatten().astype(np.float32)

    def _encode_remote(self, image_path) -> np.ndarray:
        """通过 HTTP 调远程视觉服务。"""
        import requests
        from pathlib import Path
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")
        with open(p, "rb") as f:
            r = requests.post(
                f"{self._remote_url}/encode",
                files={"image": (p.name, f, "image/jpeg")},
                timeout=30,
            )
        r.raise_for_status()
        vec = np.array(r.json()["embedding"], dtype=np.float32)
        n = np.linalg.norm(vec) + 1e-8
        return vec / n

    # ---------- 缓存管理 ----------

    def upsert(self, item_id: str, image_path: str | os.PathLike) -> np.ndarray:
        if not self.is_ready():
            self.load()
        if not image_path or not Path(image_path).exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")
        vec = self.encode_image(image_path)
        if item_id in self._id_to_idx:
            idx = self._id_to_idx[item_id]
            self._emb_array[idx] = vec
        else:
            idx = len(self._idx_to_id)
            self._emb_array = np.vstack([self._emb_array, vec.reshape(1, -1)]) if self._emb_array.size else vec.reshape(1, -1)
            self._id_to_idx[item_id] = idx
            self._idx_to_id.append(item_id)
        self._save_cache()
        return vec

    def remove(self, item_id: str) -> bool:
        if item_id not in self._id_to_idx:
            return False
        idx = self._id_to_idx.pop(item_id)
        self._idx_to_id[idx] = None
        mask = np.ones(len(self._idx_to_id), dtype=bool)
        mask[idx] = False
        self._emb_array = self._emb_array[mask] if self._emb_array.size else self._emb_array[:0]
        new_idx = {}
        new_list = []
        for i, iid in enumerate(self._idx_to_id):
            if iid is not None:
                new_idx[iid] = len(new_list)
                new_list.append(iid)
        self._id_to_idx = new_idx
        self._idx_to_id = new_list
        self._save_cache()
        return True

    def get(self, item_id: str) -> np.ndarray | None:
        idx = self._id_to_idx.get(item_id)
        if idx is None or idx >= len(self._emb_array):
            return None
        return self._emb_array[idx]

    # ---------- 兼容性打分 ----------

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return 0.0
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-8
        return float(np.dot(a, b) / denom)

    def pair_score(self, a, b) -> float:
        return self.cosine(a, b)

    def outfit_compatibility(self, items: Iterable[dict]) -> tuple[float, list[float]]:
        embs = [self.get(it["id"]) for it in items]
        pairs: list[float] = []
        for i in range(len(embs)):
            for j in range(i + 1, len(embs)):
                pairs.append(self.pair_score(embs[i], embs[j]))
        if not pairs:
            return 0.0, []
        return float(np.mean(pairs)), pairs

    def has_embedding(self, item_id: str) -> bool:
        return item_id in self._id_to_idx
