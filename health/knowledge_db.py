#!/usr/bin/env python3
"""健康知识数据库 -偏口鱼博士风格"""
import json, re

# 核心知识点库
KNOWLEDGE_DB = [
    # === 食物红榜 ===
    {
        "id": "food_egg",
        "category": "食物红榜",
        "title": "鸡蛋：平价营养之王",
        "summary": "一天2-3个鸡蛋，胜过海参燕窝虫草。蛋白质姓蛋！",
        "details": "鸡蛋含有完整蛋白质、DHA、磷脂酰丝氨酸(PS)。笨鸡蛋和普通鸡蛋营养几乎一样，别花冤枉钱。鸡腿肉也富含PS，补脑效果好。",
        "recommend": "推荐",
        "tags": ["蛋白质", "补脑", "DHA", "PS"]
    },
    {
        "id": "food_milk",
        "category": "食物红榜",
        "title": "牛奶：补钙第一选择",
        "summary": "骨头汤补不了钙，喝牛奶才是正解。每天一杯奶。",
        "details": "骨头里的钙不溶于水，煮再久也出不来。牛奶含钙高、吸收好，是真正有效的补钙方式。",
        "recommend": "推荐",
        "tags": ["补钙", "蛋白质", "骨骼"]
    },
    {
        "id": "food_veg",
        "category": "食物红榜",
        "title": "深色蔬菜：颜色越深越好",
        "summary": "紫洋葱、西兰花、绿叶菜，整吃别打粉，果蔬粉是智商税。",
        "details": "深色蔬菜富含膳食纤维、维生素、抗氧化物质。要整吃，别打成粉或汁。果蔬粉、纤维汁全是智商税。",
        "recommend": "推荐",
        "tags": ["膳食纤维", "维生素", "抗氧化"]
    },
    {
        "id": "food_potato",
        "category": "食物红榜",
        "title": "土豆：比米饭更好的主食",
        "summary": "土豆升糖指数比白米饭低，富含膳食纤维和维生素。",
        "details": "精制碳水（白米饭、白粥、白面条）升糖快，建议用土豆、玉米、地瓜、荞麦、杂豆替代。",
        "recommend": "推荐",
        "tags": ["主食", "膳食纤维", "低升糖"]
    },
    {
        "id": "food_fish",
        "category": "食物红榜",
        "title": "深海鱼：Omega-3宝库",
        "summary": "青鱼、鲭鱼、三文鱼富含Omega-3（DHA+EPA），对孩子补脑、中老年人清理血管都有用。",
        "details": "Omega-3分DHA和EPA：DHA对孩子好（用脑多、用眼多、记忆力差）；EPA适合中老年人（清理血管垃圾）。深海鱼是最好来源，坚果也有但热量高。",
        "recommend": "推荐",
        "tags": ["Omega-3", "DHA", "EPA", "补脑", "血管"]
    },
    {
        "id": "food_meat",
        "category": "食物红榜",
        "title": "肉蛋奶：蛋白质优先来源",
        "summary": "必须吃肉蛋奶，反对纯素。蛋白质来源首选：肉>蛋>奶>鱼>豆制品。",
        "details": "纯素饮食伤大脑、伤体质。孕妇、产妇、健身人群更需要多吃肉蛋奶。白肉（鸡、鱼）为主，红肉（牛羊猪）为辅，红白搭配最健康。",
        "recommend": "推荐",
        "tags": ["蛋白质", "肉蛋奶", "纯素误区"]
    },

    # === 智商税黑榜 ===
    {
        "id": "tax_soup",
        "category": "智商税黑榜",
        "title": "汤类：营养在肉里不在汤里",
        "summary": "骨头汤、鸡汤、五谷粥——汤里主要是热水加油脂，营养还在肉里。",
        "details": "汤里蛋白质和矿物质大部分留在肉里，喝进去的主要是脂肪和嘌呤。想补钙喝牛奶，想补蛋白吃肉。粥没一点营养，别当饭吃。",
        "recommend": "不推荐",
        "tags": ["骨头汤", "鸡汤", "智商税", "补钙误区"]
    },
    {
        "id": "tax_birdnest",
        "category": "智商税黑榜",
        "title": "燕窝/阿胶/虫草/灵芝孢子粉",
        "summary": "阿胶是驴皮加红糖，燕窝美容不如鸡蛋，虫草灵芝无特别功效。",
        "details": "燕窝的美容功效远不如鸡蛋。阿胶胶原蛋白是劣质蛋白。正常吃肉蛋奶蔬菜粗粮，什么补剂都不用买。",
        "recommend": "不推荐",
        "tags": ["燕窝", "阿胶", "虫草", "灵芝", "智商税"]
    },
    {
        "id": "tax_fruitjuice",
        "category": "智商税黑榜",
        "title": "果汁/奶茶/水果：高糖陷阱",
        "summary": "水果高糖，一天不超过200g；果汁更不健康，好果不打汁。",
        "details": "水果里的果糖只能靠肝脏代谢，吃多了易脂肪肝。长一辈不吃水果也没事。果汁打汁后果糖更浓缩，奶茶、饮料、蜂蜜水同理。",
        "recommend": "不推荐",
        "tags": ["水果", "果汁", "高糖", "脂肪肝"]
    },
    {
        "id": "tax_redSugar",
        "category": "智商税黑榜",
        "title": "红糖水：补血是假的",
        "summary": "红糖铁含量微乎其微，想补血吃猪肝。",
        "details": "红糖让你舒服是因为它是糖——热量让你暂时缓解，不是真的补血。想补铁：吃红肉、吃动物肝脏。",
        "recommend": "不推荐",
        "tags": ["红糖", "补血", "智商税", "铁"]
    },
    {
        "id": "tax_chickenfeet",
        "category": "智商税黑榜",
        "title": "鸡爪/猪蹄：劣质蛋白",
        "summary": "鸡爪猪蹄胶原蛋白是劣质蛋白，吃了也不会变成脸上的胶原蛋白。",
        "details": "胶原蛋白进入人体被分解成氨基酸，不可能直接补充到皮肤。鸡爪猪蹄蛋白质质量不高，别指望美容。",
        "recommend": "不推荐",
        "tags": ["鸡爪", "猪蹄", "胶原蛋白", "劣质蛋白"]
    },
    {
        "id": "tax_healthwater",
        "category": "智商税黑榜",
        "title": "养生茶/神奇水/碱性水",
        "summary": "养生茶跟养生两个字挂钩就没用；矿泉水、碱性水、气泡水都是营销概念。",
        "details": "沙棘原浆、人参原浆是高糖饮料。喝水就喝白水，自来水烧开就行。目标是把尿喝白。一天1.5-2升，少喝烫水（伤食道）。",
        "recommend": "不推荐",
        "tags": ["养生茶", "碱性水", "矿泉水", "智商税"]
    },
    {
        "id": "tax_fruitpowder",
        "category": "智商税黑榜",
        "title": "果蔬粉/纤维汁/补硒水",
        "summary": "正常吃饭不会缺微量元素，补多了反而中毒。",
        "details": "果蔬粉、纤维汁、补硒水全是营销概念。微量元素的最好来源是正常饮食，不是保健品。补多了反而中毒。",
        "recommend": "不推荐",
        "tags": ["果蔬粉", "纤维汁", "补硒", "智商税"]
    },

    # === 健康习惯 ===
    {
        "id": "habit_sleep",
        "category": "健康习惯",
        "title": "睡眠：抗衰老的基础",
        "summary": "睡好美容觉比任何护肤程序都重要，睡眠是最好的抗衰老手段。",
        "details": "皮肤35岁后断崖式衰老，底层弹力纤维网流失。睡眠是抗衰老基础，睡好觉比复杂护肤程序更重要。",
        "recommend": "重要",
        "tags": ["睡眠", "抗衰老", "美容觉"]
    },
    {
        "id": "habit_sunscreen",
        "category": "健康习惯",
        "title": "防晒：抗衰老第一防线",
        "summary": "年轻时做好防晒补水，比以后花大钱做医美更有效。",
        "details": "防晒是预防皮肤衰老的第一道防线。高糖饮食会糖化胶原蛋白，导致皮肤老化。过烫的水洗脸也伤皮肤。",
        "recommend": "重要",
        "tags": ["防晒", "抗衰老", "胶原蛋白", "糖化"]
    },
    {
        "id": "habit_emotion",
        "category": "健康习惯",
        "title": "情绪管理：负面情绪是细胞的氧化压力源",
        "summary": "气大伤身，负面情绪会让细胞氧化受损，保持好心态本身就是健康投资。",
        "details": "不良情绪、熬夜、抽烟喝酒都会让细胞氧化受损。抗氧化物质（如葡萄籽、白藜芦醇、番茄红素）可以帮助对抗细胞氧化。",
        "recommend": "重要",
        "tags": ["情绪", "氧化", "抗衰老", "气大伤身"]
    },
    {
        "id": "habit_phone",
        "category": "健康习惯",
        "title": "用眼习惯：看手机要开灯，别躺着看",
        "summary": "关灯看手机伤眼睛，躺着看更伤。",
        "details": "看手机要开灯，别躺着看。侧着刷牙别横着刷。洗澡别猛搓皮肤。这些小习惯长期影响健康。",
        "recommend": "重要",
        "tags": ["用眼", "手机", "护眼"]
    },
    {
        "id": "habit_facial",
        "category": "健康习惯",
        "title": "护肤：面膜只有补水有用",
        "summary": "面膜只有补水有用，抗衰美白成分进不去皮肤。射频/超声每年不超过2次。",
        "details": "皮肤吸收能力有限，面膜中抗衰美白成分绝大多数进不去皮肤表层以下。射频/超声仪每年不超过2次，过度使用伤皮肤。",
        "recommend": "重要",
        "tags": ["护肤", "面膜", "医美"]
    },

    # === 营养素详解 ===
    {
        "id": "nut_omega3",
        "category": "营养素详解",
        "title": "Omega-3：不饱和脂肪酸",
        "summary": "Omega-3分DHA（孩子补脑）和EPA（中老年清血管）。深海鱼是最好来源。",
        "details": "油脂分三种：反式脂肪酸最坏（完全不吃）、饱和脂肪酸少吃（动物油）、不饱和脂肪酸要多补（鱼油、鱼肝油、橄榄油）。Omega-3是不饱和脂肪酸的代表。",
        "recommend": "推荐",
        "tags": ["Omega-3", "不饱和脂肪酸", "DHA", "EPA"]
    },
    {
        "id": "nut_ps",
        "category": "营养素详解",
        "title": "磷脂酰丝氨酸(PS)：提升专注力和记忆力",
        "summary": "PS存在于鲭鱼、青鱼、鳗鱼、鸡腿肉中，补脑效果明显。考前吃鸡腿有科学依据。",
        "details": "磷脂酰丝氨酸(PS)是提升记忆力和专注力的关键营养素。富含PS的食物：鲭鱼、青鱼、鳗鱼、鸡腿肉。搭配Omega-3效果更佳。",
        "recommend": "推荐",
        "tags": ["PS", "磷脂酰丝氨酸", "补脑", "记忆力"]
    },
    {
        "id": "nut_bvitamins",
        "category": "营养素详解",
        "title": "B族维生素：存在于谷物壳中",
        "summary": "B族维生素有助于儿童生长发育、预防脱发，吃糙米可补充。",
        "details": "B族维生素存在于谷物壳中，精米白面去掉了这些。糙米、全谷物是B族维生素的好来源，有助于儿童生长发育、预防脱发。",
        "recommend": "推荐",
        "tags": ["B族维生素", "糙米", "谷物", "儿童发育"]
    },
    {
        "id": "nut_vita",
        "category": "营养素详解",
        "title": "维生素A/C/E/番茄红素：抗氧化",
        "summary": "抗氧化物质帮助对抗细胞氧化：葡萄籽、白藜芦醇、番茄（番茄红素）。",
        "details": "氧化是细胞损伤的重要原因。抗氧化物质包括：维生素A、C、E、葡萄籽、白藜芦醇、番茄红素、花青素。多吃深色蔬菜和水果补充。",
        "recommend": "推荐",
        "tags": ["抗氧化", "维生素", "番茄红素", "花青素"]
    },

    # === 体检与就医 ===
    {
        "id": "med_exam",
        "category": "体检与就医",
        "title": "体检频率建议",
        "summary": "不同年龄段体检重点不同，35岁后重点关注代谢指标。",
        "details": "常规体检建议：30岁前每2年一次，30-40岁每年一次，40岁后每年两次。关注：血糖、血脂、血压、肝功能、甲状腺。特定职业（熬夜多、饮酒多）要针对性加项。",
        "recommend": "重要",
        "tags": ["体检", "血糖", "血脂", "血压"]
    },
    {
        "id": "med_liver",
        "category": "体检与就医",
        "title": "肝脏健康：最沉默的器官",
        "summary": "肝脏没有痛觉神经，轻度损伤往往感觉不到，等发现就是中晚期。",
        "details": "伤肝行为：喝酒、熬夜、乱吃药（尤其是中药偏方）、高糖饮食。护肝：少喝酒、规律作息、不乱吃药、多吃深色蔬菜。",
        "recommend": "重要",
        "tags": ["肝脏", "护肝", "酒精", "熬夜"]
    },
    {
        "id": "med_digest",
        "category": "体检与就医",
        "title": "消化系统：胃肠道健康",
        "summary": "肠胃问题多与饮食结构相关，调理优先于药物。",
        "details": "胃酸、胃痛、反酸：少吃刺激性食物（咖啡、辣、油腻），规律进餐。肠易激综合征：减少高FODMAP食物（乳制品、豆类、洋葱等）。便秘：多喝水、补膳食纤维、多运动。",
        "recommend": "重要",
        "tags": ["肠胃", "消化", "便秘", "胃酸"]
    },

    # === 运动与康复 ===
    {
        "id": "sport_basic",
        "category": "运动与康复",
        "title": "运动处方：因人而异",
        "summary": "有氧+力量+柔韧三合一才完整，每周150分钟中等强度有氧是底线。",
        "details": "最佳运动组合：有氧（跑步游泳） + 力量（深蹲俯卧撑） + 柔韧（拉伸）。久坐人群每30分钟起身活动一次。膝盖不好推荐游泳而非跑步。",
        "recommend": "重要",
        "tags": ["有氧", "力量", "柔韧", "久坐"]
    },
    {
        "id": "sport_rehab",
        "category": "运动与康复",
        "title": "常见运动损伤处理",
        "summary": "急性损伤（RICE原则）：Rest休息、Ice冰敷、Compression加压、Elevation抬高。",
        "details": "崴脚后第一时间冰敷+制动，别热敷乱揉。慢性劳损（腰肌劳损、肩周炎）：理疗+针对性拉伸+加强核心肌群力量。椎间盘突出：卧床休息为主，避免弯腰搬重物。",
        "recommend": "重要",
        "tags": ["运动损伤", "崴脚", "腰肌劳损", "RICE"]
    },

    # === 特定人群 ===
    {
        "id": "crowd_pregnant",
        "category": "特定人群",
        "title": "孕产妇营养指南",
        "summary": "孕期一人吃两人补：蛋白质翻倍，叶酸补足，铁和钙要额外关注。",
        "details": "孕早期重点：叶酸（防神经管畸形）、碘。孕中晚期重点：蛋白质、铁（防贫血）、钙+D（促进胎儿骨骼发育）。产后重点：继续补铁补钙，优质蛋白促进伤口愈合。",
        "recommend": "重要",
        "tags": ["孕妇", "叶酸", "铁", "钙", "蛋白质"]
    },
    {
        "id": "crowd_elder",
        "category": "特定人群",
        "title": "中老年健康重点",
        "summary": "40岁后关注血管（EPA清血管）、骨骼（钙+D）、肌肉（蛋白质+力量）。",
        "details": "中老年核心关注：心脑血管（Omega-3 EPA）、骨骼（钙+维生素D+晒太阳）、肌肉（蛋白质+力量训练防肌少症）、认知（PS+DHA）。每年体检加项：颈动脉彩超、骨密度。",
        "recommend": "重要",
        "tags": ["中老年", "血管", "骨骼", "肌肉", "认知"]
    },
    {
        "id": "crowd_kid",
        "category": "特定人群",
        "title": "儿童营养重点",
        "summary": "早餐别吃红薯（产气不顶饿），推荐鸡蛋牛奶全麦面包。补脑用DHA+PS。",
        "details": "儿童早餐：推荐鸡蛋、牛奶、全麦面包、土豆、杂粮粥；不推荐大米白粥（升糖快）和红薯（易产气）。用脑多、近视、注意力不集中的孩子补充Omega-3（DHA）和PS。糙米补充B族维生素。",
        "recommend": "重要",
        "tags": ["儿童", "早餐", "DHA", "补脑", "B族维生素"]
    },
]

# 饮食核心公式
DIET_FORMULA = "肉蛋奶(优质蛋白) + 深色蔬菜(纤维维生素) + 粗粮主食(玉米地瓜荞麦杂豆) + 少糖少果 + 多喝白水"

# 核心金句
KEY_QUOTES = [
    "蛋白质，它姓蛋！鸡蛋能顶海参他爷！",
    "养生锅、养生杯、养生茶——凡是带养生俩字的基本都是智商税。",
    "好果不打汁，好肉不做馅！",
    "喝汤真不如吃肉！营养在肉里，不在汤里！",
    "正常吃饭不会缺微量元素，补多了反而中毒。",
    "水果高糖，一辈子不吃也没事！",
    "皮肤35岁后断崖式衰老，睡眠是最好的抗衰老手段。",
    "气大伤身，负面情绪是细胞的氧化压力源。",
    "防晒是预防皮肤衰老的第一道防线。",
    "只要正常吃肉蛋奶蔬菜粗粮，什么补剂都不用买。"
]

def search(query, top_k=5):
    """搜索相关知识"""
    query = query.lower()
    results = []
    for item in KNOWLEDGE_DB:
        score = 0
        if query in item['title'].lower(): score += 10
        if query in item['summary'].lower(): score += 5
        if query in item['details'].lower(): score += 3
        for tag in item['tags']:
            if query in tag.lower(): score += 2
        if query in item['category'].lower(): score += 1
        if score > 0:
            results.append((score, item))
    results.sort(key=lambda x: -x[0])
    return [r[1] for r in results[:top_k]]

def get_by_category(category):
    return [k for k in KNOWLEDGE_DB if k['category'] == category]

def get_all_categories():
    cats = {}
    for k in KNOWLEDGE_DB:
        cats[k['category']] = cats.get(k['category'], 0) + 1
    return cats

def answer_question(query):
    """基于知识库回答问题"""
    hits = search(query, top_k=3)
    if not hits:
        return {
            "answer": "这个问题我还没有收录相关知识，可以试试问更具体的关键词。",
            "sources": [],
            "tips": KEY_QUOTES[:2]
        }
    context = "\n\n".join([
        f"【{h['title']}】{h['summary']}\n{h['details']}"
        for h in hits
    ])
    return {
        "answer": context,
        "sources": [{"title": h['title'], "category": h['category']} for h in hits],
        "tips": [q for q in KEY_QUOTES if any(h['id'] in q or h['title'] in q for h in hits)][:2]
    }