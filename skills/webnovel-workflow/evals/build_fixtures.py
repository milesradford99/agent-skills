"""Build four sample novel archives for resume evals. Usage: python3 build_fixtures.py <out_dir>"""
import shutil
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "references" / "tools"
sys.path.insert(0, str(TOOLS))
import context  # noqa: E402
import novel  # noqa: E402

OUT = Path(sys.argv[1])

CHARACTERS = """# 人物

只记不太会变的东西。位置、伤势、当前知道什么、手里有什么，记在 记录-人物现状.md。

## 林晚
- 别名：师姐、林师姐、晚晚
- 身份、来历：青云宗外门弟子，管后山药园，入门五年
- 想做成什么，为什么在意：考进内门，给病重的弟弟换一颗九转丹
- 最怕失去什么：弟弟
- 性格、缺点和底线：嘴硬心软，记仇，不害无辜
- 说话：对师弟师妹碎碎念，对上头的人客气但不低头

## 顾长风
- 别名：顾师兄、长风、大师兄
- 身份、来历：内门首席，林晚的同乡
- 想做成什么，为什么在意：查清十年前家里那桩灭门案
- 最怕失去什么：线索
- 性格、缺点和底线：话少，什么都自己扛，不骗林晚
- 说话：短句，被问急了就沉默

## 赵三
- 别名：无
- 身份、来历：药园杂役，第2章死于后山塌方
- 性格：胆小，嘴碎，对林晚好
"""

CURRENT = """# 人物现状

写到最新采用的一章为止。只记会变的东西，不变的特征在 03-人物.md。每个人物一节，标题和 03-人物.md 里的名字一样。

## 林晚
- 状态：在场
- 现在在哪，身体和情绪怎样：后山药园，右手被药锄划伤，心里憋着火
- 眼下想做什么：查清是谁偷了丹方那一页
- 知道的事：丹方少了一页；赵三死前说看见有人半夜进过药园
- 误以为的事：以为偷丹方的是外门的周管事
- 手里有什么：药园钥匙
- 和谁的关系到了哪一步：和顾长风三年没说过话，第3章他来药园，她没理
- 最近更新：第3章

## 顾长风
- 状态：在场
- 现在在哪，身体和情绪怎样：内门，左肩有旧伤
- 眼下想做什么：找丹方缺的那一页，那页上有灭门案的线索
- 知道的事：缺页上写着一个人名
- 手里有什么：首席令牌
- 和谁的关系到了哪一步：想跟林晚说话，开不了口
- 最近更新：第3章

## 赵三
- 状态：死亡（第2章后山塌方）
- 现在在哪，身体和情绪怎样：已下葬
- 最近更新：第2章
"""

SETTINGS = """# 设定

只记已确认的设定。没确认的放在最后“待定”里。一次事件不自己总结成通用规则。

## 世界与生活
- 时代、地点、故事开始时的环境：青云宗，一个中等修仙门派
- 普通人怎么生活，向往什么：外门弟子靠种药换贡献点，攒够了考内门

## 重要地点和物品
每个地点、物品、组织一小节，标题是正文里最常用的叫法，第一行写别名。工具按名字从细纲里找出要读的条目。

### 后山药园
- 别名：药园
- 是什么、在哪、归谁：外门种灵药的地方，林晚管着
- 规则、限制和现状：夜里落锁，钥匙只有林晚和执法堂有

### 九转丹方
- 别名：丹方
- 是什么、在哪、归谁：宗门秘传丹方，藏在药园石室
- 规则、限制和现状：第2章发现少了最后一页

### 执法堂
- 别名：无
- 是什么、在哪、归谁：管门规的地方
- 规则、限制和现状：有药园的备用钥匙

## 尚未揭示
已确认、但正文还没写到的真相和后续安排。写正文时不能提前让人物知道，也不能记成已经发生。资料包每章都带这一节，但它不进独立读者的事实清单。
- 顾长风是掌门的私生子，他自己不知道

## 待定
还没经作者确认的候选设定。
- 无
"""

FORESHADOW = """# 伏笔

没收的写在前面，收掉的挪到最后。没收的伏笔不管多久以前埋的，都留在这里。

## 没收的
### F001
- 涉及：林晚、九转丹方、顾长风
- 内容：丹方最后一页被撕走，页上写着一个人名
- 读者从第几章起知道多少：第2章知道少了一页，不知道写了什么
- 埋在第几章，原文怎么写的（一句）：第2章，“石匣里只剩一道齐整的撕痕”
- 现在进展到哪：林晚在查
- 预计什么时候、什么条件下收：第一卷末

### F002
- 涉及：执事、执法堂
- 内容：执法堂的执事左手少两根手指，伤是十年前留的
- 读者从第几章起知道多少：第3章提到执事戴手套
- 埋在第几章，原文怎么写的（一句）：第3章，“执事的左手一直揣在袖子里”
- 现在进展到哪：只露了手套
- 预计什么时候、什么条件下收：第一卷中段

## 已收的
### F003
- 涉及：赵三
- 内容：赵三欠赌债，第2章收（他死后林晚替他还了）
"""

DROPPED = """# 废弃设定

作者推翻的设定记在这里，防止换对话以后被写回来。

## D001
- 原来是什么：顾长风是林晚失散的亲哥哥
- 为什么废：作者不要血缘梗，两人是同乡
- 被什么替代：同乡，小时候一起长大
- 作者哪次定的：开书第四步
"""

RESOURCES = """# 资源

## R001
- 谁的：林晚
- 是什么：铜钱
- 当前数量和限制：10 枚
- 最近一次变化：第3章，卖药材得了 4 枚
"""

TIMELINE_LINES = {
    1: "- 第001章：林晚在药园发现灵药被人半夜挖过",
    2: "- 第002章：后山塌方，赵三死；林晚发现九转丹方少了最后一页，替赵三还了赌债",
    3: "- 第003章：三天后，顾长风来药园，林晚没理他；执法堂执事来查塌方，左手揣在袖子里",
}

CHAPTERS = {
    1: """# 第1章 夜里的锄印

天还没亮，林晚就蹲在药园东头，盯着一排被翻开的土。

土是新的，带着露水。三株紫心草连根没了，坑边留着一道锄印，比她的药锄窄一指。

“谁啊这是。”她嘀咕着，用手比了比锄印，又抬头看篱笆。篱笆上的锁好好挂着，一点撬过的痕迹都没有。

赵三拎着水桶从小路上过来，看见她的脸色，脚步就慢了。

“师姐，又丢了？”

“三株。”林晚站起来拍土，“你昨晚睡得死不死？”

“死，死得很。”赵三缩了缩脖子，“不过……半夜好像听见门响了一声，我以为是风。”

林晚没说话，转身去看石室的门。门也锁着。她摸了摸腰上的钥匙，钥匙还在。

药园的钥匙，只有她和执法堂有。
""",
    2: """# 第2章 撕痕

后山塌下来的时候，林晚正在石室里点数。

地动了一下，架子上的药罐叮叮当当响成一片。她扶住石壁等了一会儿，外面有人在喊，喊的是赵三的名字。

她跑出去，后山半边坡都没了。赵三的水桶滚在路边，人没找到。

挖到傍晚才挖出来。

林晚在他身边坐了很久。旁边有人说，赵三还欠着赌坊六枚铜钱，这下可好，债主上哪儿要去。她听见了，回屋数了六枚，第二天一早送了过去。

那天夜里她睡不着，又进了石室。九转丹方装在最里头的石匣里，她打开来，想看看弟弟那颗丹到底要多少药材。

丹方还在，可最后一页没了。石匣里只剩一道齐整的撕痕。

她想起赵三说的，半夜门响了一声。
""",
    3: """# 第3章 三年

三天以后，顾长风来了药园。

林晚在给紫心草补苗，听见脚步声也没抬头。那脚步她认得，三年没听过，还是认得。

“晚晚。”

她手里的苗插歪了。她拔出来，重新插。

“塌方的事，执法堂让我来看看。”顾长风站在篱笆外头，没进来，“你手怎么了？”

右手上那道口子是昨天药锄划的，她把袖子往下拉了拉。

“顾首席忙，看完就回吧。”

顾长风没走。他站了很久，久到林晚把一垄苗都补完了。后来执法堂的执事也来了，一个瘦高的中年人，查塌方查得很细，左手一直揣在袖子里，偶尔拿出来，戴着一只灰手套。

执事走的时候，顾长风也走了。他回头看了她一眼，像是有话要说，最后什么也没说。

林晚把药锄往地上一插。她卖了三天药材，攒了四枚铜钱，加上原来的，一共十枚。不够一颗九转丹的零头。
""",
}


def set_status(project, pairs):
    path = project / "01-项目状态.md"
    text = path.read_text(encoding="utf-8")
    for section, key, value in pairs:
        text = context.set_field(text, section, key, value)
    path.write_text(text, encoding="utf-8")


def write(project, name, text):
    path = project / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def base_book(project):
    novel.init_project(project, resources=True)
    write(project, "03-人物.md", CHARACTERS)
    write(project, "记录-人物现状.md", CURRENT)
    write(project, "02-设定.md", SETTINGS)
    write(project, "记录-伏笔.md", FORESHADOW)
    write(project, "记录-废弃设定.md", DROPPED)
    write(project, "记录-资源.md", RESOURCES)
    write(project, "记录-时间线.md", "# 时间线\n\n按章记，每章一两句，只记会影响后面的事。故事里过了多少天、多少年，也记在这里。\n\n")
    write(project, "04-大纲.md", "# 大纲\n\n## 故事框架\n- 外门弟子林晚为救弟弟查丹方缺页，牵出顾长风的灭门旧案。\n\n### 作者确认的卖点\n- 嘴硬心软的药园师姐，一边种药一边破案\n\n## 分卷纲\n### 第一卷：药园\n- 林晚查丹方缺页，和顾长风从互不说话到联手。\n\n## 当前细纲\n\n## 已写\n")
    rules = (project / "00-写作规则.md").read_text(encoding="utf-8")
    write(project, "00-写作规则.md", rules)
    for section, key, value in (
        ("现在在哪", "书名", "药园师姐"), ("现在在哪", "当前阶段", "写正文"),
        ("正文进度", "每章目标字数", "1500"),
    ):
        set_status(project, [(section, key, value)])
    for number in (1, 2, 3):
        draft = write(project, f"待确认/第{number:03d}章-v2-候选.md", CHAPTERS[number])
        novel.adopt_chapter(project, number, draft)
        timeline = project / "记录-时间线.md"
        timeline.write_text(timeline.read_text(encoding="utf-8") + TIMELINE_LINES[number] + "\n", encoding="utf-8")
        set_status(project, [("交接", "更新于", f"第{number}章后，11-1{number}")])
        result = novel.finish_writeback(project)
        assert result["closed"], result["errors"]
    # the records above were written as of chapter 3; rewrite them after the adopt cycle
    write(project, "记录-人物现状.md", CURRENT)
    write(project, "记录-资源.md", RESOURCES)
    set_status(project, [("正文进度", "定稿参照章", "第2章")])
    status = (project / "01-项目状态.md").read_text(encoding="utf-8")
    status = status.replace("：未开始（作者可以选择跳过）", "：已完成").replace("：未开始（未开始／待修改／可以试写）", "：可以试写").replace("：未开始\n", "：已确认\n")
    write(project, "01-项目状态.md", status)


OUTLINE_4 = """### 第4章：撞见
- 出场：林晚、顾长风、执事、九转丹方、后山药园
- 伏笔：F001、F002
- 夜里林晚守在药园，撞见顾长风撬开石室翻丹方石匣。她以为偷丹方的就是他，两人在石室里对峙。顾长风只说“那页纸上有我要找的东西”，不肯多讲。执事提着灯巡夜过来，林晚把顾长风推进药架后面挡住，自己应付执事，说是来点药。执事看了一眼石匣，左手在袖子里动了动，走了。林晚得到：知道顾长风也在找缺页；失去：对周管事的怀疑。最值得展开的：石室里两人三年后第一次说话。章尾停在执事走后，顾长风问她为什么护着他。

### 第5章：灯
- 出场：林晚、顾长风
- 伏笔：F001
- 林晚没回答，让他先说清楚那页纸。顾长风讲了灭门案的一半。章尾林晚答应帮他，条件是找到丹方后先给弟弟配药。
"""


def handover(project, stop, notes):
    set_status(project, [
        ("交接", "更新于", "第3章后，11-13"),
        ("交接", "上次停在哪", stop),
        ("交接", "作者最近的指示", "11-13：第4章别让林晚当场揭穿或告发顾长风，她嘴上凶，心里不信他是贼"),
        ("交接", "被否掉的方向", "顾长风黑化成反派——作者说他不是坏人，以后也不会是"),
        ("交接", "当前张力", "丹方缺页是谁拿的；林晚和顾长风三年不说话的心结"),
        ("交接", "接下来一到三章要拉回的注意力", notes),
        ("正文进度", "当前细纲", "覆盖到第几章：第5章；检查过没有：检查过；作者确认没有：确认了"),
    ])


def fixture_resume(out):
    project = out / "书"
    base_book(project)
    outline = project / "04-大纲.md"
    outline.write_text(outline.read_text(encoding="utf-8").replace("## 当前细纲\n", "## 当前细纲\n" + OUTLINE_4), encoding="utf-8")
    handover(project, "第3章回写完成；第4章细纲作者已确认，还没动笔", "执事的手套（第3章露过一次）")
    set_status(project, [("现在在哪", "下一步", "写第4章")])
    return project


CHAPTER_4 = """# 第4章 撞见

三更天，药园里起了雾。

林晚抱着膝盖坐在石室对面的草垛后头，已经守了两个时辰。腿麻了，她也不动。

门响的时候，她差点没听见。那人没用钥匙，是从窗子翻进去的，落地很轻。

她摸进去，一把扯住那人的袖子。灯一晃，照出一张她三年没正眼看过的脸。

“顾长风。”

他手里攥着石匣的盖子，没松。

“那页纸上有我要找的东西。”他只说了这一句。

外头有灯光晃过来，是执事巡夜。林晚想都没想，把他往药架后面一推，自己迎了出去。

“来点药。”她说，“紫心草夜里点数准。”

执事提着灯，看了一眼石匣，又看了她一眼。他的左手在袖子里动了动，没拿出来。

“早点歇着。”他走了。

林晚回头，顾长风从药架后头出来，肩上蹭了一道灰。

“为什么护着我？”

她没回答。她从荷包里摸出两枚铜钱，丢给他：“明天去山下买点伤药，你那肩膀，我看着烦。”
"""


def fixture_interrupted(out):
    project = fixture_resume(out)
    draft = write(project, "待确认/第004章-v2-候选.md", CHAPTER_4)
    novel.adopt_chapter(project, 4, draft)
    current = project / "记录-人物现状.md"
    text = current.read_text(encoding="utf-8")
    text = text.replace("- 误以为的事：以为偷丹方的是外门的周管事", "- 误以为的事：无（第4章撞见顾长风后，不再怀疑周管事）")
    text = text.replace("- 和谁的关系到了哪一步：和顾长风三年没说过话，第3章他来药园，她没理\n- 最近更新：第3章",
                        "- 和谁的关系到了哪一步：第4章三年来第一次和顾长风说话，替他挡了执事\n- 最近更新：第4章")
    current.write_text(text, encoding="utf-8")
    resources = project / "记录-资源.md"
    resources.write_text(resources.read_text(encoding="utf-8").replace("- 当前数量和限制：10 枚\n- 最近一次变化：第3章，卖药材得了 4 枚",
                                                                     "- 当前数量和限制：8 枚\n- 最近一次变化：第4章，给顾长风 2 枚买伤药"), encoding="utf-8")
    return project


def fixture_dead(out):
    project = out / "书"
    base_book(project)
    outline = project / "04-大纲.md"
    outline.write_text(outline.read_text(encoding="utf-8").replace("## 当前细纲\n", """## 当前细纲
### 第4章：药种
- 出场：林晚、赵三、后山药园
- 伏笔：F001
- 清早赵三在药园门口等林晚，递给她一包紫心草的药种，说是从后山捡的，又说那天半夜进药园的人穿着内门的衣服。林晚得到：内门这条线索；失去：无。最值得展开的：赵三递药种时的样子。章尾停在林晚看向内门的方向。

### 第5章：内门
- 出场：林晚、顾长风
- 伏笔：F001
- 林晚去内门找人，撞上顾长风。
"""), encoding="utf-8")
    handover(project, "第3章回写完成；第4章细纲作者已确认，还没动笔", "无")
    set_status(project, [("现在在哪", "下一步", "写第4章")])
    return project


def fixture_interview(out):
    project = out / "书"
    novel.init_project(project)
    record = project / "05-开书记录.md"
    text = record.read_text(encoding="utf-8")
    text = text.replace("## 进行中\n开书某一步做到一半时的过程记录：访谈每一轮的问题和作者的原话、还没交给作者的方案草稿放在哪。每轮问完就追加，换对话以后从最后一轮接着问，不重问。这一步做完、结论写进下面对应的一节以后，清空这一节。\n- 无",
                        """## 进行中
开书某一步做到一半时的过程记录：访谈每一轮的问题和作者的原话、还没交给作者的方案草稿放在哪。每轮问完就追加，换对话以后从最后一轮接着问，不重问。这一步做完、结论写进下面对应的一节以后，清空这一节。
- 背景（11-12）：没有现成脑洞；没写过小说；在医院药房干了八年；喜欢《庆余年》《夜的命名术》。
- 第1轮（11-12）问：最近追完、熬夜看的是哪本，哪一段？答：“《夜的命名术》里庆尘在监狱里一点点摸清规矩那段，看得停不下来。”
- 第2轮（11-12）问：有没有看到一半弃的？在哪儿弃的？答：“好几本修仙，主角一上来就无敌，打脸打到第五十章我就腻了。”
- 第3轮（11-12）问：给了三个开局场面让挑（当众翻盘／忍下来夜里自己动手／被意想不到的人护住）。答：“第二个，我喜欢主角憋着、心里有数、一点点来。”
- 第4轮（11-12）问：希望读者读完是什么感觉？答：“像看完一个人靠本事在陌生地方站住脚，踏实，有点暖。”
- 目前六样：主角——有了（憋得住、心里有数、靠专业本事）；最想看的场面——有了（摸清规矩、暗里布局）；读完的感受——有了（踏实、有点暖）；作者熟悉的行业——有了（医院药房）；一定不写的——还没问；平台和篇幅——还没问。"""
                        )
    record.write_text(text, encoding="utf-8")
    set_status(project, [
        ("现在在哪", "当前阶段", "开书"),
        ("现在在哪", "下一步", "开书第一步：接着访谈"),
        ("交接", "更新于", "第0章后，11-12（开书访谈中）"),
        ("交接", "上次停在哪", "开书第一步访谈第4轮问完，作者说今天先到这"),
    ])
    status = project / "01-项目状态.md"
    status.write_text(status.read_text(encoding="utf-8").replace("1. 弄清想写什么：未开始", "1. 弄清想写什么：进行中（访谈问到第4轮，记录在 05-开书记录.md 的“进行中”）"), encoding="utf-8")
    return project


def fixture_adopt(out):
    """Chapter 4 candidate is ready and the author is about to adopt it."""
    project = fixture_resume(out)
    write(project, "待确认/第004章-v2-候选.md", CHAPTER_4)
    set_status(project, [
        ("正文进度", "正在写", "第4章"),
        ("正文进度", "这一章的进度", "待作者确认"),
        ("正文进度", "这一章的自检", "自查"),
        ("正文进度", "当前唯一候选", "待确认/第004章-v2-候选.md"),
        ("现在在哪", "下一步", "等作者确认第4章候选"),
        ("交接", "上次停在哪", "第4章 v2 候选交给作者了，等他确认"),
    ])
    return project


def fixture_drift(out):
    """正文 has chapter 4 (dropped in by the author outside the workflow); the status still says 3."""
    project = fixture_resume(out)
    write(project, "正文/第004章.md", CHAPTER_4)
    return project


ACCEPTED_HEADER = "## 作者接受的偏差\n作者看过、说了“这个不管”“先这样”的问题，一条一行，写哪天定的。以后不再提，除非它会坏的事变了。\n- 无"
DECISIONS_HEADER = "## 最近的决定\n最近十个决定，每条：定了什么／谁定的（作者、作者按推荐确认、按推荐）／一句理由。更早的挪进卷总结或开书记录。\n- 无"


def replace_in_status(project, old, new):
    path = project / "01-项目状态.md"
    text = path.read_text(encoding="utf-8")
    assert old in text, old[:30]
    path.write_text(text.replace(old, new), encoding="utf-8")


def fixture_status_card(out):
    project = fixture_resume(out)
    replace_in_status(project, DECISIONS_HEADER, DECISIONS_HEADER.replace("- 无",
        "- 第4–5章细纲按推荐排／作者按推荐确认／先让两人在石室重逢\n- 定稿参照章用第2章／作者／他最喜欢第2章的节奏"))
    return project


def fixture_accepted(out):
    project = fixture_resume(out)
    replace_in_status(project, ACCEPTED_HEADER, ACCEPTED_HEADER.replace("- 无",
        "- 11-13：每章三四百字就行，不用按 1500 写（作者说手机上读短章更顺）\n- 11-13：“本书的写法”先不总结，写满十章再说\n- 11-13：周管事这条线先放着，以后再说"))
    replace_in_status(project, "- 合作方式：带着写（带着写／搭档／作者执笔；作者的合作偏好也记在这里，比如“细纲不用给我看”“不用解释为什么”）",
                      "- 合作方式：搭档（不用解释为什么；待确认事项最多一条）")
    return project


AUTHOR_DRAFT_4 = CHAPTER_4.replace("右手的口子", "左手的口子") if "右手的口子" in CHAPTER_4 else CHAPTER_4.replace(
    "林晚抱着膝盖坐在石室对面的草垛后头，已经守了两个时辰。腿麻了，她也不动。",
    "林晚抱着膝盖坐在石室对面的草垛后头，已经守了两个时辰。腿麻了，她也不动。左手上那道药锄划的口子一跳一跳地疼。")


def fixture_author_writes(out):
    project = fixture_resume(out)
    replace_in_status(project, "- 合作方式：带着写（带着写／搭档／作者执笔；作者的合作偏好也记在这里，比如“细纲不用给我看”“不用解释为什么”）",
                      "- 合作方式：作者执笔（正文我自己写，你帮我审读和记账）")
    write(project, "待确认/第004章-作者稿.md", AUTHOR_DRAFT_4)
    set_status(project, [
        ("正文进度", "正在写", "第4章"),
        ("正文进度", "这一章的进度", "作者交稿，待审读"),
        ("正文进度", "当前唯一候选", "待确认/第004章-作者稿.md"),
        ("现在在哪", "下一步", "审读作者交来的第4章"),
    ])
    return project


FATE_CHARACTERS = CHARACTERS.replace("- 性格、缺点和底线：嘴硬心软，记仇，不害无辜",
    "- 性格、缺点和底线：嘴硬心软，记仇，不害无辜\n- 最在乎、最自认的（一句话）：待填写\n- 终局方向（作者定）：待定").replace(
    "- 性格、缺点和底线：话少，什么都自己扛，不骗林晚",
    "- 性格、缺点和底线：话少，什么都自己扛，不骗林晚\n- 最在乎、最自认的（一句话）：待填写\n- 终局方向（作者定）：待定") + """
## 林小满
- 别名：小满、弟弟
- 身份、来历：林晚的弟弟，十二岁，生来经脉有损，靠药吊着命
- 想做成什么，为什么在意：不想再拖累姐姐，偷偷跟着杂役学认药
- 最怕失去什么：姐姐
- 性格、缺点和底线：乖，心思重，什么都憋着
- 最在乎、最自认的（一句话）：待填写
- 终局方向（作者定）：待定

## 沈执事
- 别名：执事、执法堂执事
- 身份、来历：执法堂执事，左手少两根手指，十年前顾家灭门案的经手人之一
- 想做成什么，为什么在意：坐上执法堂长老的位子，把当年的事永远埋住
- 最怕失去什么：名声和位子
- 性格、缺点和底线：细，稳，从不亲自动手
- 最在乎、最自认的（一句话）：待填写
- 终局方向（作者定）：待定
"""


def fixture_fate(out):
    """Opening step 4: world and characters confirmed, full-book story not yet written."""
    project = out / "书"
    novel.init_project(project)
    write(project, "03-人物.md", FATE_CHARACTERS)
    write(project, "02-设定.md", SETTINGS)
    write(project, "04-大纲.md", "# 大纲\n\n## 故事框架\n- 待填写（开书 4.2 写）\n\n### 作者确认的卖点\n- 嘴硬心软的药园师姐，一边种药一边破案\n\n## 分卷纲\n### 第一卷：药园\n- 待填写\n\n## 当前细纲\n\n## 已写\n")
    record = project / "05-开书记录.md"
    text = record.read_text(encoding="utf-8")
    text = text.replace("## 作者想写什么\n访谈后总结的六样：主角是什么样的人、最想看的两三种场面、希望读者读完的感受、一定不写的、平台和篇幅、作者熟悉的生活或行业。你替作者补的要标明。另记一句“读者一路盼的那条线”。\n- 待填写",
        "## 作者想写什么\n访谈后总结的六样：主角是什么样的人、最想看的两三种场面、希望读者读完的感受、一定不写的、平台和篇幅、作者熟悉的生活或行业。你替作者补的要标明。另记一句“读者一路盼的那条线”。\n"
        "- 主角：嘴硬心软、靠本事说话的女主，不靠男人救\n- 最想看的场面：用药理破案；两个憋着话的人终于把话说开\n"
        "- 读完的感受：“哭过以后觉得值，不要从头虐到尾”\n- 一定不写的：女主被羞辱、感情线狗血误会拖几十章\n- 平台和篇幅：番茄，60 万字左右，三卷\n"
        "- 作者熟悉的：医院药房，八年\n- 读者一路盼的那条线：丹方缺页背后的真相，和林晚、顾长风的心结")
    text = text.replace("## 选定的故事方案\n三个方案的简介、作者选了哪个、为什么，以及作者要求的修改。没选的方案留着，标“未选”。\n- 待填写",
        "## 选定的故事方案\n三个方案的简介、作者选了哪个、为什么，以及作者要求的修改。没选的方案留着，标“未选”。\n"
        "- 选定方案二《药园师姐》：外门弟子林晚为救病弱的弟弟查九转丹方的缺页，牵出顾长风家十年前的灭门案；凶手链条指向执法堂。作者要求：弟弟不能只是工具人，要有自己的戏；顾长风不黑化。\n- 方案一、三：未选")
    record.write_text(text, encoding="utf-8")
    set_status(project, [
        ("现在在哪", "书名", "药园师姐"), ("现在在哪", "当前阶段", "开书"),
        ("现在在哪", "投稿平台", "番茄"),
        ("现在在哪", "下一步", "开书 4.2：讲完整本书的故事"),
        ("交接", "更新于", "开书第4步，11-13"),
        ("交接", "上次停在哪", "4.1 世界和人物作者确认了，4.2 全书故事还没动"),
        ("交接", "被否掉的方向", "顾长风黑化；感情线靠误会拖"),
    ])
    status = project / "01-项目状态.md"
    s = status.read_text(encoding="utf-8")
    for i, value in ((1, "已确认"), (2, "已完成"), (3, "已确认")):
        s = s.replace(f"{i}. ", f"{i}. ", 1)
    s = s.replace("1. 弄清想写什么：未开始", "1. 弄清想写什么：已确认").replace("2. 看看读者在看什么：未开始（作者可以选择跳过）", "2. 看看读者在看什么：跳过")
    s = s.replace("3. 三个故事方案：未开始", "3. 三个故事方案：已确认（方案二）").replace("4. 世界、人物和全书故事：未开始", "4. 世界、人物和全书故事：进行中（4.1 已确认，4.2 没开始）")
    status.write_text(s, encoding="utf-8")
    return project


def main():
    builders = {"续写": fixture_resume, "回写中断": fixture_interrupted, "死人出场": fixture_dead, "访谈中断": fixture_interview,
                "作者采用": fixture_adopt, "状态漂移": fixture_drift,
                "状态卡": fixture_status_card, "已接受偏差": fixture_accepted, "作者执笔": fixture_author_writes,
                "开书命运": fixture_fate}
    for name, build in builders.items():
        folder = OUT / name
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        project = build(folder)
        errors, warnings = context.check_project(project)
        print(name, project, "errors:", errors, "warnings:", warnings)


if __name__ == "__main__":
    main()
