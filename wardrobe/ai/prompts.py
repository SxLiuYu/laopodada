"""
LLM 提示词模板
- Qwen3-4B-Thinking 模型专用
- 任务：对 6 套候选搭配做精排 + 写推荐理由
"""

RERANK_SYSTEM = """你是用户的私人穿搭顾问。用户告诉你天气、场合和 6 套候选搭配（按规则+视觉预评分排序），你要做：

1. 重新排序（从最值得穿到最不值得穿）
2. 给每套写 1 句中文推荐理由，<30 字，口语化、有画面感
3. 严格基于衣物信息推理，不要凭空编造

输出要求：
- 必须是合法 JSON，不要 ``` 包裹，不要任何额外说明
- 字段: {"order": ["id1","id2",...], "reasons": {"id1":"...","id2":"..."}}
- order 长度等于候选数；reasons 必须覆盖 order 中每个 id
"""


def build_rerank_prompt(weather: dict, occasion: str, candidates: list[dict]) -> str:
    """
    构造精排 prompt。
    candidates: 至少包含 id, items(list), rule_score, visual_score
    """
    lines = []
    lines.append(f"## 天气")
    lines.append(f"城市: {weather.get('city', '未知')}, 温度: {weather.get('temp', '?')}°C, "
                 f"体感: {weather.get('feels_like', '?')}°C, 天气: {weather.get('desc', '?')}, "
                 f"湿度: {weather.get('humidity', '?')}%, 风力: {weather.get('wind', '?')}km/h")
    lines.append("")
    lines.append(f"## 场合: {occasion}")
    lines.append("")
    lines.append("## 候选搭配 (6 套，按规则+视觉分预排序)")
    for i, c in enumerate(candidates, 1):
        items_desc = []
        for it in c["items"]:
            tags = " ".join([
                f"[{it.get('category','?')}]",
                f"颜色:{it.get('color','?')}",
                f"风格:{it.get('style','?')}",
                f"厚度:{it.get('warmth','?')}",
            ])
            items_desc.append(f"  - {it.get('name','?')} {tags}")
        lines.append(f"### 候选 {i} (id={c['id']})")
        lines.append(f"规则分:{c.get('rule_score', 0):.1f}  视觉分:{c.get('visual_score', 0):.2f}")
        lines.extend(items_desc)
        lines.append("")

    lines.append("## 任务")
    lines.append("输出 JSON: {\"order\":[...], \"reasons\":{...}}")
    return "\n".join(lines)
