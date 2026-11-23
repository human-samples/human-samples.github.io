#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人间样本 · 静态站生成器
把 source/data.json + source/_work/out_b*.json（脱敏结果）渲染成可被搜索引擎抓取的静态页面。

产出：
  index.html              首页（服务端渲染，列出全部条目）
  p/<id>.html             每条样本一页
  c/<slug>.html           分类索引页
  intro.html              关于页（收录标准 / 脱敏声明）
  sitemap.xml / robots.txt
  library.html            原交互版（noindex，由 git mv 保留，本脚本不动它）
"""
import json, os, re, html, datetime, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://human-samples.github.io"
SITE_NAME = "人间样本"
TAGLINE = "真实人物的性格切片与处事样本 · 写作者的人物原型库"

CAT_SLUG = {
    "顶级人类": "legends",
    "社会切片": "society",
    "娱乐圈": "entertainment",
    "商界狠人": "business",
    "情感战场": "relationships",
    "原生家庭": "family",
}

CAT_INTRO = {
    "顶级人类": "把一件事做到无人能替代的人。他们的共同点不是天赋，是在某个具体环节上反复死磕的方式——这里记录的是那个方式本身。",
    "社会切片": "普通人被一件小事卷进舆论漩涡之后的行为轨迹。看他们在没有话语权的处境里，怎么解释、怎么沉默、怎么反击。",
    "娱乐圈": "公众人设与真实选择之间的裂缝。每条都尽量保留具体动作：谁在哪一步做了什么，而不是谁被评价成什么样。",
    "商界狠人": "权力现场里的取舍。记录他们怎么定价、怎么切割、怎么把人从棋盘上拿走，以及为此付出的代价。",
    "情感战场": "亲密关系里的攻防结构：谁在用感情结算利益，谁在把让步包装成牺牲。",
    "原生家庭": "父母与子女之间的长期拉扯。重点不是谁更坏，而是那套说法是怎么一代代传下去的。",
}

CAT_PAGE_TITLE = {
    "顶级人类": "人物志 · 把一件事做到无人能替代的人",
    "社会切片": "社会切片 · 普通人被舆论卷进去之后",
    "娱乐圈": "娱乐圈 · 人设与真实选择之间的裂缝",
    "商界狠人": "商界狠人 · 权力现场里的取舍",
    "情感战场": "情感战场 · 亲密关系里的攻防结构",
    "原生家庭": "原生家庭 · 父母与子女的长期拉扯",
}

E = lambda s: html.escape(str(s or ""), quote=True)

TODAY = datetime.date.today().isoformat()


def short_desc(text, n=112):
    """按句号切分，凑到 n 字以内，避免 meta description 被截断在半句。"""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= n:
        return text
    out = ""
    for sent in re.split(r"(?<=[。！？])", text):
        if not sent:
            continue
        if len(out) + len(sent) > n:
            break
        out += sent
    return out or text[:n]


def load_items():
    """单一公开数据源：source/data_public.json
    顶级人类 → 人物志（真名，附公开来源）
    其余      → 原型库（脱敏，无来源链接）
    """
    data = json.load(open(os.path.join(ROOT, "source/data_public.json"), encoding="utf-8"))
    items = []
    for it in data["items"]:
        it = dict(it)
        it["kind"] = "person" if it["category"] == "顶级人类" else "prototype"
        items.append(it)
    return items, data


def page_shell(title, desc, canonical, body, jsonld=None, og_type="website", noindex=False):
    ld = ""
    if jsonld:
        ld = '<script type="application/ld+json">%s</script>' % json.dumps(jsonld, ensure_ascii=False, separators=(",", ":"))
    robots = '<meta name="robots" content="noindex,nofollow"/>' if noindex else '<meta name="robots" content="index,follow,max-image-preview:large"/>'
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}"/>
{robots}
<link rel="canonical" href="{E(canonical)}"/>
<meta property="og:type" content="{og_type}"/>
<meta property="og:site_name" content="{SITE_NAME}"/>
<meta property="og:title" content="{E(title)}"/>
<meta property="og:description" content="{E(desc)}"/>
<meta property="og:url" content="{E(canonical)}"/>
<meta name="twitter:card" content="summary"/>
{ld}
<style>
:root{{
  --paper:#faf9f6; --surface:#fff; --ink:#202a30; --ink2:#303c42; --ink3:#59656b; --ink4:#8a9498;
  --line:#dfe4e1; --line-soft:#e9ede9; --sunk:#f0f2ee;
  --accent:#176b75; --accent-soft:#176b7514; --hot:#b3402a; --hot-soft:#b3402a0f;
  --amber:#b8873a;
  --serif:"Songti SC","STSong","Source Han Serif SC","Noto Serif SC",Georgia,serif;
}}
*{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--paper);color:var(--ink);
  font:16px/1.78 system-ui,-apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased}}
a{{color:inherit;text-decoration:none}}
.wrap{{max-width:760px;margin:0 auto;padding:0 24px}}
header.top{{border-bottom:1px solid var(--line-soft);background:rgba(250,249,246,.92);
  position:sticky;top:0;z-index:9;backdrop-filter:blur(8px)}}
.top-in{{max-width:760px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;gap:14px}}
.mark{{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;flex:none;
  background:linear-gradient(140deg,var(--accent),#145f68);color:#fff;font-size:13px;font-weight:800}}
.brand{{font-weight:700;letter-spacing:.02em;font-size:15px}}
.brand small{{display:block;font-weight:400;font-size:10px;letter-spacing:.14em;color:var(--ink4)}}
nav.m{{margin-left:auto;display:flex;gap:18px;font-size:13px;color:var(--ink3)}}
nav.m a:hover{{color:var(--accent)}}
main{{padding:44px 0 72px}}
.crumb{{font-size:12px;color:var(--ink4);margin-bottom:22px}}
.crumb a:hover{{color:var(--accent)}}
h1{{font-family:var(--serif);font-size:34px;line-height:1.35;margin:0 0 10px;letter-spacing:.01em;font-weight:700}}
.sub{{color:var(--ink3);font-size:15px;margin:0 0 6px}}
.meta{{font-size:12px;color:var(--ink4);display:flex;flex-wrap:wrap;gap:12px;margin:16px 0 0}}
.tag{{display:inline-block;padding:3px 9px;border-radius:999px;background:var(--accent-soft);
  color:var(--accent);font-size:11px;margin:0 6px 6px 0}}
.lede{{font-family:var(--serif);font-size:19px;line-height:1.85;color:var(--ink2);margin:26px 0 0;
  padding:22px 24px;background:var(--surface);border:1px solid var(--line);border-radius:12px}}
h2{{font-size:13px;letter-spacing:.16em;color:var(--ink4);font-weight:700;margin:42px 0 14px;
  text-transform:uppercase}}
h2::before{{content:"";display:inline-block;width:14px;height:1px;background:var(--accent);
  vertical-align:middle;margin-right:9px}}
ol.methods{{margin:0;padding:0;list-style:none;counter-reset:m}}
ol.methods li{{counter-increment:m;position:relative;padding:0 0 0 34px;margin:0 0 16px;line-height:1.8}}
ol.methods li::before{{content:counter(m,decimal-leading-zero);position:absolute;left:0;top:1px;
  font:700 11px/1.9 ui-monospace,Menlo,monospace;color:var(--accent)}}
ul.plain{{margin:0;padding-left:19px}}
ul.plain li{{margin:0 0 9px;line-height:1.8}}
.tl{{margin:0;padding:0;list-style:none;border-left:1px solid var(--line)}}
.tl li{{position:relative;padding:0 0 20px 22px;line-height:1.8}}
.tl li::before{{content:"";position:absolute;left:-4px;top:9px;width:7px;height:7px;border-radius:50%;
  background:var(--paper);border:1.5px solid var(--accent)}}
.tl b{{display:block;font-size:12px;letter-spacing:.06em;color:var(--accent);font-weight:700;margin-bottom:2px}}
blockquote{{margin:0 0 12px;padding:12px 18px;border-left:2px solid var(--amber);
  background:var(--surface);font-family:var(--serif);font-size:16px;line-height:1.9;color:var(--ink2)}}
.note{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px 22px;
  line-height:1.9;font-size:15px;color:var(--ink2)}}
.grid2{{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));margin:0}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:15px 16px;
  display:block;transition:.16s}}
.card:hover{{border-color:var(--accent);transform:translateY(-2px)}}
.card b{{font-family:var(--serif);font-size:16px;display:block;margin-bottom:5px}}
.card span{{font-size:12.5px;color:var(--ink3);line-height:1.6;display:block}}
.card em{{font-style:normal;font-size:11px;color:var(--accent);letter-spacing:.06em}}
.sect{{margin:52px 0 0}}
.sect > h2{{margin-top:0}}
.pager{{display:flex;justify-content:space-between;gap:16px;margin:52px 0 0;padding-top:24px;
  border-top:1px solid var(--line-soft);font-size:13px}}
.pager a{{color:var(--accent)}}
footer{{border-top:1px solid var(--line-soft);padding:30px 0 60px;font-size:12px;color:var(--ink4);line-height:2}}
footer a{{color:var(--ink3);border-bottom:1px solid var(--line)}}
.hero{{padding:18px 0 0}}
.hero h1{{font-size:40px}}
.hero p{{font-size:16.5px;color:var(--ink3);max-width:620px;line-height:1.9}}
.rows{{border-top:1px solid var(--line-soft);margin-top:8px}}
.row{{display:flex;gap:14px;padding:14px 2px;border-bottom:1px solid var(--line-soft);align-items:baseline}}
.row a{{font-family:var(--serif);font-size:16px;font-weight:600;flex:none;min-width:8em}}
.row span{{font-size:13px;color:var(--ink3);line-height:1.65}}
.row em{{font-style:normal;margin-left:auto;font-size:11px;color:var(--ink4);flex:none}}
@media(max-width:640px){{
  h1{{font-size:27px}} .hero h1{{font-size:31px}} nav.m{{gap:12px;font-size:12px}}
  .top-in{{padding:12px 18px}} .wrap{{padding:0 18px}} .row{{flex-wrap:wrap}} .row em{{margin-left:0}}
  .lede{{font-size:17px;padding:18px}}
}}
</style>
</head>
<body>
<header class="top"><div class="top-in">
  <div class="mark">样</div>
  <a class="brand" href="/">人间样本<small>RENJIAN SAMPLES</small></a>
  <nav class="m"><a href="/">首页</a><a href="/c/legends.html">人物志</a><a href="/yuanxing.html">原型库</a><a href="/intro.html">关于</a></nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">
  <p><b>人间样本</b> · {E(TAGLINE)}</p>
  <p>原型库条目均为脱敏改写，不含真实姓名与可识别信息；人物志条目整理自公开报道，来源标注于页内。<br/>
  <a href="/intro.html">收录标准与免责声明</a> · <a href="/sitemap.xml">站点地图</a></p>
</div></footer>
</body>
</html>
"""


def kind_label(it):
    return "人物志" if it["kind"] == "person" else "原型库"


def item_url(it):
    return f"{SITE}/p/{it['id']}.html"


def render_item(it, all_items):
    cat = it["category"]
    name = it["name"]
    identity = it.get("identity", "")
    headline = it.get("headline", "")
    summary = it.get("summary", "")

    title = f"{name}：{identity.split('·')[0].strip()}｜{kind_label(it)}｜{SITE_NAME}"
    if len(title) > 62:
        title = f"{name}｜{kind_label(it)}｜{SITE_NAME}"
    desc = short_desc(summary)
    if len(desc) < 60:
        desc = short_desc(summary + " " + identity)

    tags = "".join(f'<span class="tag">{E(t)}</span>' for t in it.get("traits", [])[:6])

    sec = []
    sec.append(f"""<div class="crumb"><a href="/">首页</a> › <a href="/c/{CAT_SLUG[cat]}.html">{E(kind_label(it) if it["kind"] == "person" else cat)}</a> › <span>{E(name)}</span></div>
<h1>{E(name)}</h1>
<p class="sub">{E(identity)}</p>
<div>{tags}</div>
<div class="meta"><span>{E(kind_label(it))}</span><span>{E(cat)}</span><span>整理于 {E(it.get('date',''))}</span></div>""")

    sec.append(f'<p class="lede">{E(summary)}</p>')

    if it.get("methods"):
        sec.append("<h2>具体是怎么做的</h2><ol class='methods'>" +
                   "".join(f"<li>{E(m)}</li>" for m in it["methods"]) + "</ol>")

    if it.get("story"):
        sec.append("<h2>时间线</h2><ul class='tl'>" +
                   "".join(f"<li><b>{E(s.get('t',''))}</b>{E(s.get('d',''))}</li>" for s in it["story"]) + "</ul>")

    if it.get("quotes"):
        sec.append("<h2>原话</h2>" + "".join(f"<blockquote>{E(q)}</blockquote>" for q in it["quotes"]))

    if it.get("writingUse"):
        sec.append(f"<h2>写作怎么用</h2><div class='note'>{E(it['writingUse'])}</div>")

    n = it.get("novel") or {}
    pairs = [("想要什么", n.get("want")), ("最怕什么", n.get("fear")),
             ("矛盾点", n.get("contradiction")), ("压力下的选择", n.get("pressureChoice")),
             ("可写的场景", n.get("scene")), ("关系网", n.get("relations"))]
    pairs = [(k, v) for k, v in pairs if v]
    if pairs:
        sec.append("<h2>角色参数</h2><div class='note'>" +
                   "".join(f"<p style='margin:0 0 10px'><b>{E(k)}</b>：{E(v)}</p>" for k, v in pairs) + "</div>")

    if it["kind"] == "prototype":
        sec.append("<h2>关于这一条</h2><div class='note' style='font-size:14px'>本条为<b>脱敏原型</b>："
                   "已删除真实姓名、机构与精确可检索信息，保留的是行为结构与心理机制，用于小说、剧本的人物塑造。"
                   "如与你认识的人相似，那是原型层面的普遍性，不指向任何具体个人。</div>")
    elif it.get("sources"):
        sec.append("<h2>参考来源</h2><ul class='plain'>" + "".join(
            f'<li><a href="{E(s["url"])}" rel="noopener nofollow" target="_blank">{E(s["title"])}</a>'
            f'　<span style="color:var(--ink4);font-size:12px">{E(s.get("publisher",""))}</span></li>'
            for s in it["sources"]) + "</ul>")

    # 相关
    same = [x for x in all_items if x["category"] == cat and x["id"] != it["id"]][:4]
    if same:
        sec.append("<h2>同类样本</h2><div class='grid2'>" + "".join(
            f"<a class='card' href='/p/{E(x['id'])}.html'><b>{E(x['name'])}</b>"
            f"<span>{E((x.get('identity') or '').split('·')[0].strip())}</span></a>" for x in same) + "</div>")

    sec.append(f"""<div class="pager"><a href="/c/{CAT_SLUG[cat]}.html">← 更多{E(cat)}样本</a><a href="/">回到首页 →</a></div>""")

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": (headline if it["kind"] == "prototype" else f"{name}：{identity}") or f"{name}：{identity}",
        "description": desc,
        "datePublished": it.get("date", TODAY),
        "dateModified": TODAY,
        "inLanguage": "zh-CN",
        "author": {"@type": "Organization", "name": SITE_NAME},
        "publisher": {"@type": "Organization", "name": SITE_NAME, "url": SITE},
        "mainEntityOfPage": {"@type": "WebPage", "@id": item_url(it)},
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE},
        "keywords": "、".join(it.get("traits", [])[:6]),
    }
    if it["kind"] == "person":
        jsonld["about"] = {"@type": "Person", "name": name, "description": identity}

    return page_shell(title, desc, item_url(it), "\n".join(sec), jsonld, "article")


def render_home(items):
    persons = [x for x in items if x["kind"] == "person"]
    protos = [x for x in items if x["kind"] == "prototype"]
    protos.sort(key=lambda x: -x.get("heat", 0))
    cats = ["社会切片", "娱乐圈", "商界狠人", "情感战场", "原生家庭"]

    rows = "".join(
        f"<div class='row'><a href='/p/{E(x['id'])}.html'>{E(x['name'])}</a>"
        f"<span>{E((x.get('identity') or '').split('·')[0].strip())}　{E((x.get('headline') or '')[:46])}</span>"
        f"<em>{E(x['category'])}</em></div>" for x in protos)

    body = f"""<section class="hero">
<h1>人间样本</h1>
<p>这里不写“他性格偏执”这种结论，只记录<b>具体动作</b>：谁在哪一步说了什么、让谁承担了代价。<br/>
人物志是真人传记，原型库是脱敏后的性格切片——都用一句话说清“这个人是怎么办事的”。</p>
</section>

<section class="sect">
<h2>人物志 · {len(persons)} 位真人</h2>
<p style="color:var(--ink3);font-size:14.5px;margin:-4px 0 14px;max-width:640px">
把一件事做到无人能替代的人。读他们，看的是一个人在具体环节上死磕的方式，可以整段搬进小说。</p>
<div class="grid2">""" + "".join(
        f"<a class='card' href='/p/{E(x['id'])}.html'><b>{E(x['name'])}</b>"
        f"<span>{E(x.get('identity') or '')}</span></a>" for x in persons) + f"""</div>
</section>

<section class="sect">
<h2>原型库 · {len(protos)} 个脱敏原型</h2>
<p style="color:var(--ink3);font-size:14.5px;margin:-4px 0 14px;max-width:640px">
全部去掉真名与可识别细节，只留行为机制。写控制型母亲、写被消耗的人、写翻车后的辩解，直接从这里挑。</p>
<div class="rows">{rows}</div>
</section>

<section class="sect">
<h2>按分类进入</h2>
<div class="grid2">""" + "".join(
        f"<a class='card' href='/c/{CAT_SLUG[c]}.html'><b>{E(c)}</b><span>{E(CAT_PAGE_TITLE[c].split(' · ')[1])}</span>"
        f"<em>{len([x for x in items if x['category']==c])} 条</em></a>" for c in cats + ["顶级人类"]) + """</div>
</section>

<section class="sect">
<h2>关于收录</h2>
<div class="note">人物志条目整理自公开报道，页内标注来源；原型库条目经过脱敏改写，不含真实姓名、机构名与精确可检索信息。
完整收录标准与免责声明见 <a href="/intro.html" style="color:var(--accent)">关于页</a>。</div>
</section>
"""

    desc = f"人间样本收录 {len(persons)} 位真人传记与 {len(protos)} 个脱敏性格原型，每条写清「具体怎么做的」，供小说、剧本的人物塑造参考。"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "alternateName": TAGLINE,
        "url": SITE + "/",
        "description": desc,
        "inLanguage": "zh-CN",
    }
    return page_shell(f"人间样本 · 真人传记与性格原型库（{len(items)} 条）", desc, SITE + "/", body, jsonld)


def render_category(cat, items):
    subset = [x for x in items if x["category"] == cat]
    persons = [x for x in subset if x["kind"] == "person"]
    protos = [x for x in subset if x["kind"] == "prototype"]
    slug = CAT_SLUG[cat]

    parts = [f"""<div class="crumb"><a href="/">首页</a> › <span>{E(cat)}</span></div>
<h1>{E(CAT_PAGE_TITLE[cat])}</h1>
<p class="lede">{E(CAT_INTRO[cat])}</p>
<p style="color:var(--ink4);font-size:12px;margin-top:18px">共 {len(subset)} 条</p>"""]

    for group, label in ((persons, "人物志"), (protos, "脱敏原型")):
        if not group:
            continue
        parts.append(f"<h2>{label}</h2><div class='rows'>" + "".join(
            f"<div class='row'><a href='/p/{E(x['id'])}.html'>{E(x['name'])}</a>"
            f"<span>{E((x.get('identity') or '').split('·')[0].strip())}</span></div>" for x in group) + "</div>")

    parts.append('<div class="pager"><a href="/">← 回到首页</a><a href="/c/legends.html">人物志 →</a></div>')

    desc = f"{CAT_INTRO[cat][:80]}共 {len(subset)} 条，含{'、'.join(x['name'] for x in subset[:5])}等。"[:150]
    title = f"{CAT_PAGE_TITLE[cat]}（{len(subset)} 条）｜{SITE_NAME}"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": CAT_PAGE_TITLE[cat],
        "description": desc,
        "url": f"{SITE}/c/{slug}.html",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE},
    }
    return page_shell(title, desc, f"{SITE}/c/{slug}.html", "\n".join(parts), jsonld)


def render_about(items):
    persons = len([x for x in items if x["kind"] == "person"])
    protos = len([x for x in items if x["kind"] == "prototype"])
    body = f"""<div class="crumb"><a href="/">首页</a> › <span>关于</span></div>
<h1>关于人间样本</h1>
<p class="sub">一个给小说、剧本作者用的人物素材库</p>

<p class="lede">写作卡住的时候，多数人缺的不是文笔，是「这个人具体会怎么做」。这里收集的是动作，不是形容词。</p>

<h2>收录什么</h2>
<div class="note">
<p style="margin:0 0 10px"><b>人物志（{persons} 条）</b>：把一件事做到无人能替代的真人——科学家、翻译家、劳模、手艺人。整理自公开报道与公开资料，页内逐条标注来源，可直接核对。</p>
<p style="margin:0 0 10px"><b>原型库（{protos} 条）</b>：从公共事件里抽出来的性格切片。真实姓名、机构、精确金额与日期已全部删除或泛化，只保留行为结构、心理机制和关系网。这些条目不指向任何可识别的个人。</p>
<p style="margin:0">每条都尽量回答同一个问题：<b>他/她具体是怎么做的</b>——分几步、在哪个环节让了、代价落到了谁身上。</p>
</div>

<h2>脱敏原则</h2>
<div class="note">
<p style="margin:0 0 10px">原型库条目在发布前经过统一处理：删除全部人名（含亲属、对手）、机构与品牌名、节目与作品名、精确金额、市级以下地名、可被检索命中一手引语；时间模糊到年月或相对时点。</p>
<p style="margin:0">保留的是因果、动机与防御方式。如果某条让你想起身边的人，那是原型层面的普遍性，不是指认。</p>
</div>

<h2>怎么用</h2>
<div class="note">
<p style="margin:0 0 10px">1. 先按分类找结构：控制型父母、翻车后的辩解、权力现场的切割。<br/>
2. 抄「具体怎么做的」那一栏去改造你的角色，别抄评价。<br/>
3. 页底的「写作怎么用」和「角色参数」是给卡文时用的脚手架。</p>
</div>

<h2>免责与联系</h2>
<div class="note" style="font-size:14px">
本站为写作参考工具，不提供新闻、不评价具体个人、不构成任何事实认定。原型库不含可识别个人信息；人物志内容如有事实错误或来源失效，欢迎指正，会据实修订或删除。<br/>
联系：<a href="mailto:hello@human-samples.github.io" style="color:var(--accent)">hello@human-samples.github.io</a>
</div>

<div class="pager"><a href="/">← 回到首页</a><a href="/c/legends.html">看人物志 →</a></div>
"""
    desc = f"人间样本是什么：{persons} 位真人传记 + {protos} 个脱敏性格原型，收录标准、脱敏原则与免责声明。"
    return page_shell(f"关于人间样本 · 收录标准与脱敏原则｜{SITE_NAME}", desc, f"{SITE}/intro.html", body)


def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)
    return len(content)


def render_prototypes(items):
    protos = [x for x in items if x["kind"] == "prototype"]
    protos.sort(key=lambda x: -x.get("heat", 0))
    blocks = []
    for cat in ["社会切片", "娱乐圈", "商界狠人", "情感战场", "原生家庭"]:
        group = [x for x in protos if x["category"] == cat]
        if not group:
            continue
        blocks.append(f"<h2>{E(cat)} · {len(group)} 条</h2><div class='rows'>" + "".join(
            f"<div class='row'><a href='/p/{E(x['id'])}.html'>{E(x['name'])}</a>"
            f"<span>{E((x.get('identity') or '').split('·')[0].strip())}</span></div>" for x in group) + "</div>")

    body = f"""<div class="crumb"><a href="/">首页</a> › <span>原型库</span></div>
<h1>原型库 · {len(protos)} 个脱敏性格原型</h1>
<p class="lede">全部去掉真名、机构名与可检索细节，只留行为机制。写控制型父母、写翻车后的辩解、写权力现场的切割，从这里挑人，不用怕写到真人身上。</p>
{''.join(blocks)}
<div class="pager"><a href="/">← 回到首页</a><a href="/c/legends.html">看人物志 →</a></div>
"""
    desc = f"{len(protos)} 个脱敏性格原型：控制型母亲、被消耗的人、翻车后的辩解、权力现场的取舍。全部不含真名，可直接用于小说人物塑造。"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "原型库",
        "description": desc,
        "url": SITE + "/yuanxing.html",
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE},
    }
    return page_shell(f"原型库 · {len(protos)} 个脱敏性格原型｜{SITE_NAME}", desc, SITE + "/yuanxing.html", body, jsonld)


def main():
    items, data = load_items()
    print(f"可发布条目: {len(items)}（人物志 {len([x for x in items if x['kind']=='person'])} / 原型库 {len([x for x in items if x['kind']=='prototype'])}）")

    n = 0
    for it in items:
        n += write(f"p/{it['id']}.html", render_item(it, items))
    print(f"  样本页 {len(items)} 个，{n/1024:.0f} KB")

    total = write("index.html", render_home(items))
    for cat in CAT_SLUG:
        write(f"c/{CAT_SLUG[cat]}.html", render_category(cat, items))
    write("intro.html", render_about(items))
    write("yuanxing.html", render_prototypes(items))
    print(f"  首页 {total/1024:.0f} KB，分类页 {len(CAT_SLUG)} 个，关于页 1 个")

    urls = [(SITE + "/", "1.0", "daily"), (SITE + "/yuanxing.html", "0.9", "weekly"),
            (SITE + "/intro.html", "0.8", "monthly")]
    urls += [(f"{SITE}/c/{CAT_SLUG[c]}.html", "0.8", "weekly") for c in CAT_SLUG]
    urls += [(item_url(it), "0.7", "monthly") for it in items]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, p, f in urls:
        sm.append(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod><changefreq>{f}</changefreq><priority>{p}</priority></url>")
    sm.append("</urlset>")
    write("sitemap.xml", "\n".join(sm))

    write("robots.txt", f"""User-agent: *
Allow: /

Sitemap: {SITE}/sitemap.xml
""")
    print(f"  sitemap {len(urls)} 条 URL")


if __name__ == "__main__":
    main()
