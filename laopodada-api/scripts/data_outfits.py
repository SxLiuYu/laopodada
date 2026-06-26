"""data_outfits.py — 5 个 outfit 主题(节 2.3, 节 1 outfit 示例 5 组)

实际组合由 atlas LLM 选(seed 后从返回校验),我们只提供主题。
"""

OUTFITS = [
    {
        "occasion": "work",
        "season": "fall",
        "weather": {"temp_c": 18, "condition": "cloudy"},
        "label_cn": "上班通勤",
    },
    {
        "occasion": "casual",
        "season": "fall",
        "weather": {"temp_c": 22, "condition": "sunny"},
        "label_cn": "周末休闲",
    },
    {
        "occasion": "date",
        "season": "summer",
        "weather": {"temp_c": 26, "condition": "sunny"},
        "label_cn": "正式晚宴",
    },
    {
        "occasion": "work",
        "season": "winter",
        "weather": {"temp_c": 5, "condition": "snowy"},
        "label_cn": "秋冬保暖",
    },
    {
        "occasion": "sport",
        "season": "summer",
        "weather": {"temp_c": 28, "condition": "sunny"},
        "label_cn": "夏日出行",
    },
]
