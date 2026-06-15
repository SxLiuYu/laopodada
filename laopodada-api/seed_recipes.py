"""Seed recipes into the laopodada SQLite database.

Idempotent: if the recipes table already has >=12 rows, the script exits
without inserting anything. Run from the laopodada-api/ root:

    python3 seed_recipes.py

Reuses the existing DB connection logic from app.py (same DATA_DIR / DB_PATH)
so the recipes land in the same DB gunicorn serves.
"""
import os
import sys
import time
import uuid

# Import the Flask app module so we share its DB_PATH / init logic.
# This must happen before get_db() touches the DB.
import sqlite3
import os
import sys
import time
import uuid

from app import DB_PATH, init_db

# Make sure the schema exists (no-op if it already does).
init_db()


# ---------- Seed data ----------
RECIPES = [
    # ---------- breakfast (3) ----------
    {
        "title": "小米粥",
        "category": "breakfast",
        "difficulty": "easy",
        "prep_minutes": 5,
        "cook_minutes": 30,
        "servings": 2,
        "ingredients": [
            "小米 100g",
            "清水 1500ml",
            "红枣 5 颗(可选)",
            "冰糖 少许",
        ],
        "steps": [
            "小米淘洗干净,加清水浸泡 15 分钟",
            "锅中倒入 1500ml 清水烧开",
            "下入小米,大火煮开后转小火",
            "小火慢熬 25-30 分钟,期间搅拌几次防粘底",
            "加入红枣和冰糖再煮 3 分钟即可",
        ],
        "tags": ["快手", "养胃", "中式"],
        "note": "水量可根据喜好调整,喜欢稠的少放点水。",
    },
    {
        "title": "煎蛋三明治",
        "category": "breakfast",
        "difficulty": "easy",
        "prep_minutes": 5,
        "cook_minutes": 8,
        "servings": 1,
        "ingredients": [
            "吐司面包 2 片",
            "鸡蛋 1 个",
            "生菜 2 片",
            "番茄 2 片",
            "沙拉酱 适量",
            "黄油 少许",
        ],
        "steps": [
            "平底锅小火融化黄油,打入鸡蛋煎至蛋白凝固",
            "吐司片放入烤箱或锅中略烤至微黄",
            "一片吐司抹沙拉酱,铺生菜和番茄片",
            "放上煎蛋,再盖另一片吐司",
            "对角切开即可享用",
        ],
        "tags": ["快手", "西式", "饱腹"],
        "note": "可加火腿或芝士片,口感更丰富。",
    },
    {
        "title": "燕麦杯",
        "category": "breakfast",
        "difficulty": "easy",
        "prep_minutes": 5,
        "cook_minutes": 0,
        "servings": 1,
        "ingredients": [
            "即食燕麦 50g",
            "牛奶 200ml",
            "香蕉 半根",
            "蓝莓 30g",
            "蜂蜜 1 勺",
            "坚果碎 少许",
        ],
        "steps": [
            "杯底铺一层燕麦",
            "倒入牛奶没过燕麦,静置 2 分钟让燕麦软化",
            "切香蕉片铺在中层",
            "顶部放蓝莓,淋蜂蜜",
            "撒上坚果碎即可",
        ],
        "tags": ["免煮", "健身", "高纤维"],
        "note": "前一晚做好冷藏,早上直接吃更入味。",
    },
    # ---------- lunch (3) ----------
    {
        "title": "西红柿炒蛋",
        "category": "lunch",
        "difficulty": "easy",
        "prep_minutes": 5,
        "cook_minutes": 10,
        "servings": 2,
        "ingredients": [
            "鸡蛋 3 个",
            "西红柿 2 个",
            "葱花 少许",
            "盐 适量",
            "糖 半勺",
            "食用油 2 勺",
        ],
        "steps": [
            "鸡蛋打散加少许盐搅匀",
            "西红柿切块",
            "热锅倒油,倒入蛋液炒至凝固盛出",
            "锅内余油下西红柿翻炒出汁",
            "加盐和糖调味,倒入鸡蛋翻匀",
            "撒葱花起锅",
        ],
        "tags": ["快手", "下饭", "经典"],
        "note": "加点糖能中和西红柿的酸味,口感更柔和。",
    },
    {
        "title": "清蒸鲈鱼",
        "category": "lunch",
        "difficulty": "medium",
        "prep_minutes": 10,
        "cook_minutes": 12,
        "servings": 2,
        "ingredients": [
            "鲈鱼 1 条(约 500g)",
            "姜 5 片",
            "葱 2 根",
            "蒸鱼豉油 2 勺",
            "料酒 1 勺",
            "热油 1 勺",
        ],
        "steps": [
            "鲈鱼处理干净,鱼身划几刀方便入味",
            "鱼身抹料酒,铺姜片,葱段塞鱼腹",
            "水开后大火蒸 10-12 分钟",
            "倒掉蒸出的汤汁,铺新葱丝",
            "淋蒸鱼豉油,最后浇一勺热油激香",
        ],
        "tags": ["清淡", "高蛋白", "宴客"],
        "note": "蒸的时间根据鱼大小调整,1 斤左右的鱼 10 分钟足够。",
    },
    {
        "title": "宫保鸡丁",
        "category": "lunch",
        "difficulty": "medium",
        "prep_minutes": 15,
        "cook_minutes": 15,
        "servings": 2,
        "ingredients": [
            "鸡腿肉 300g",
            "花生米 50g",
            "干辣椒 8 个",
            "花椒 1 勺",
            "葱白 2 段",
            "蒜 3 瓣",
            "生抽 2 勺",
            "醋 1 勺",
            "糖 1 勺",
            "淀粉 1 勺",
            "料酒 1 勺",
        ],
        "steps": [
            "鸡腿肉切丁,加生抽、料酒、淀粉腌 10 分钟",
            "调汁:生抽+醋+糖+少量清水搅匀",
            "热油下花椒和干辣椒爆香",
            "下鸡丁翻炒至变色,加葱蒜爆香",
            "倒入调味汁,最后撒花生米翻匀出锅",
        ],
        "tags": ["川菜", "下饭", "微辣"],
        "note": "花生米最后下,保持酥脆口感。",
    },
    # ---------- dinner (3) ----------
    {
        "title": "红烧排骨",
        "category": "dinner",
        "difficulty": "medium",
        "prep_minutes": 10,
        "cook_minutes": 40,
        "servings": 3,
        "ingredients": [
            "猪肋排 600g",
            "姜 4 片",
            "八角 2 个",
            "冰糖 30g",
            "生抽 3 勺",
            "老抽 1 勺",
            "料酒 2 勺",
            "盐 适量",
        ],
        "steps": [
            "排骨冷水下锅焯水,撇去浮沫后捞出",
            "锅中放冰糖小火熬至琥珀色",
            "下排骨翻炒上色",
            "加姜、八角、生抽、老抽、料酒",
            "倒入热水没过排骨,大火烧开转小火炖 35 分钟",
            "最后大火收汁,加盐调味",
        ],
        "tags": ["下饭", "宴客", "经典"],
        "note": "炒糖色时一定要小火,糖糊了会发苦。",
    },
    {
        "title": "清炒时蔬",
        "category": "dinner",
        "difficulty": "easy",
        "prep_minutes": 5,
        "cook_minutes": 5,
        "servings": 2,
        "ingredients": [
            "时令蔬菜 300g(菜心/油麦菜/小白菜)",
            "蒜 2 瓣",
            "盐 适量",
            "食用油 1 勺",
            "生抽 半勺",
        ],
        "steps": [
            "蔬菜洗净切段,蒜切片",
            "热锅热油爆香蒜片",
            "下青菜大火快炒",
            "加盐和生抽翻炒均匀",
            "断生即可出锅,保持翠绿",
        ],
        "tags": ["快手", "低脂", "素食"],
        "note": "大火快炒是关键,炒太久会出水变黄。",
    },
    {
        "title": "番茄牛腩",
        "category": "dinner",
        "difficulty": "hard",
        "prep_minutes": 15,
        "cook_minutes": 90,
        "servings": 4,
        "ingredients": [
            "牛腩 800g",
            "番茄 3 个",
            "洋葱 1 个",
            "番茄酱 2 勺",
            "姜 4 片",
            "八角 2 个",
            "料酒 2 勺",
            "生抽 2 勺",
            "盐 适量",
        ],
        "steps": [
            "牛腩切块冷水下锅焯水去血沫",
            "番茄去皮切块,洋葱切块",
            "热锅下少许油,炒香洋葱",
            "下牛腩翻炒,加料酒去腥",
            "加入番茄块和番茄酱炒出汁",
            "倒入热水没过牛腩,加姜、八角、生抽",
            "大火烧开转小火炖 80 分钟",
            "最后加盐调味大火收汁",
        ],
        "tags": ["硬菜", "高蛋白", "宴客"],
        "note": "炖的时间要够,牛腩才会软烂入味。",
    },
    # ---------- snack / dessert / drink (3) ----------
    {
        "title": "酸奶水果捞",
        "category": "snack",
        "difficulty": "easy",
        "prep_minutes": 10,
        "cook_minutes": 0,
        "servings": 1,
        "ingredients": [
            "浓稠酸奶 200g",
            "草莓 5 颗",
            "蓝莓 30g",
            "猕猴桃 1 个",
            "芒果 半颗",
            "麦片 少许",
            "蜂蜜 1 勺",
        ],
        "steps": [
            "所有水果洗净切丁",
            "杯底铺一层酸奶",
            "依次铺上各种水果",
            "再淋一层酸奶",
            "顶部撒麦片,淋蜂蜜",
        ],
        "tags": ["免煮", "低卡", "高纤维"],
        "note": "水果可根据季节自由搭配,香蕉牛油果也不错。",
    },
    {
        "title": "芒果班戟",
        "category": "dessert",
        "difficulty": "medium",
        "prep_minutes": 15,
        "cook_minutes": 15,
        "servings": 4,
        "ingredients": [
            "鸡蛋 2 个",
            "牛奶 240ml",
            "低筋面粉 80g",
            "黄油 15g",
            "细砂糖 30g",
            "淡奶油 200ml",
            "芒果 1 个",
        ],
        "steps": [
            "鸡蛋加糖打散,加入牛奶拌匀",
            "筛入低筋面粉搅成无颗粒面糊",
            "加入融化的黄油拌匀,过筛一次",
            "平底锅小火摊成薄饼,每张约 1 分钟",
            "淡奶油加糖打发",
            "班戟皮放凉后抹奶油,放芒果条",
            "包成长方形,冷藏 30 分钟即可",
        ],
        "tags": ["港式", "甜品", "下午茶"],
        "note": "面糊过筛后更细腻,煎出来的饼更光滑。",
    },
    {
        "title": "蜂蜜柠檬水",
        "category": "drink",
        "difficulty": "easy",
        "prep_minutes": 5,
        "cook_minutes": 0,
        "servings": 1,
        "ingredients": [
            "柠檬 2 片",
            "蜂蜜 1 勺",
            "温水 300ml",
            "薄荷叶 2 片(可选)",
        ],
        "steps": [
            "柠檬用盐搓洗后切薄片",
            "杯中先放蜂蜜",
            "倒入 60℃ 左右的温水搅匀",
            "放入柠檬片",
            "加薄荷叶装饰即可",
        ],
        "tags": ["快手", "维生素 C", "低卡"],
        "note": "水温不能太高,会破坏蜂蜜中的活性酶和维生素 C。",
    },
]


def main() -> int:
    """Idempotently insert seed recipes.

    Returns 0 always (success or already-seeded). Exits with a printed message
    so the user can see what happened.
    """
    # Use a standalone connection so close_db() teardown never fires on it.
    db = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    existing = db.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"]
    if existing >= 12:
        print(f"already seeded ({existing} recipes present)")
        return 0

    now = int(time.time())
    inserted = 0
    for r in RECIPES:
        rid = uuid.uuid4().hex[:16]
        db.execute(
            """INSERT INTO recipes
               (id, title, category, difficulty, prep_minutes, cook_minutes, servings,
                ingredients, steps, tags, note, cover_url, bytes_cover,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rid,
                r["title"],
                r["category"],
                r["difficulty"],
                r["prep_minutes"],
                r["cook_minutes"],
                r["servings"],
                "\n".join(r["ingredients"]),
                "\n".join(r["steps"]),
                ",".join(r["tags"]),
                r["note"],
                None,  # cover_url
                0,     # bytes_cover
                now,
                now,
            ),
        )
        inserted += 1

    print(f"inserted {inserted} recipes")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())