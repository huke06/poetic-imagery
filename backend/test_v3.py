# -*- coding: utf-8 -*-
"""v3 改造验收测试：对照《问题及方案.md》逐项验证后端接口与数据。

运行：cd backend && python -X utf8 test_v3.py
"""
import warnings
warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient
from app.main import app
from app import config_store
from app.config import settings

TOKEN = config_store.get_effective("ADMIN_TOKEN", settings.ADMIN_TOKEN)
PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✔ {name}")
    else:
        FAIL += 1
        print(f"  ✘ {name}  {extra}")


with TestClient(app) as c:
    h = {"X-Admin-Token": TOKEN}

    print("\n【问题1①】情感分布环形饼图（情感标签占比数据）")
    d = c.get("/api/concept/1").json()["data"]
    check("返回 emotion_tag_stats", "emotion_tag_stats" in d)
    check("含二级标签+一级类别+占比", all(k in d["emotion_tag_stats"][0]
          for k in ("emotion", "category", "ratio")) if d["emotion_tag_stats"] else False)
    cats = {s["category"] for s in d["emotion_tag_stats"]}
    check("颜色可按一级类别区分(>=2类)", len(cats) >= 2, str(cats))

    print("\n【问题1②】演变脉络折线图（朝代出现频次，九大段）")
    groups = [x["dynasty"] for x in d["dynasty_occurrence"]]
    check("九大朝代段", groups == ["先秦", "秦汉", "魏晋南北朝", "隋唐", "五代十国", "宋", "元", "明", "清"], str(groups))
    check("频次数据非空", any(x["count"] > 0 for x in d["dynasty_occurrence"]))

    print("\n【问题2①】经典名句朝代筛选：全部(下拉)+唐+宋")
    check("dynasty_stats 提供下拉朝代", len(d["dynasty_stats"]) > 0)
    r = c.get("/api/concept/1/poetries", params={"dynasty": "唐"})
    check("按唐筛选可用", r.status_code == 200 and r.json()["data"]["total"] >= 0)
    r = c.get("/api/concept/1/poetries", params={"dynasty": "宋"})
    check("按宋筛选可用", r.status_code == 200)

    print("\n【问题2②】一级情感标签可筛选名句（poetries 已标注）")
    check("返回 emotion_mains", isinstance(d.get("emotion_mains"), list) and len(d["emotion_mains"]) > 0,
          str(d.get("emotion_mains")))
    main = d["emotion_mains"][0]
    r = c.get("/api/concept/1/poetries", params={"emotion_main": main})
    items = r.json()["data"]["items"]
    check(f"按「{main}」筛选有名句", len(items) > 0)
    check("每条名句带 emotion_main 字段", all("emotion_main" in it for it in items))

    print("\n【问题3①】对仗 couplets CSV 导入（word_a/word_b/verse/poet/title）")
    couplet_csv = "word_a,word_b,verse,poet,title\n测试甲,测试乙,测试例句,测试诗人,测试题\n"
    r = c.post("/api/admin/import?dry_run=true", files=[("files", ("t.csv", couplet_csv, "text/csv"))], headers=h)
    check("CSV 识别为对仗表", "csv-couplets" in r.json()["data"]["preview"]["formats"])
    r = c.post("/api/admin/import?dry_run=false", files=[("files", ("t.csv", couplet_csv, "text/csv"))], headers=h)
    rep = r.json()["data"]["reports"][0]
    check("对仗入库成功", rep["type"] == "couplets" and rep["inserted"] == 1, str(rep))
    # 清理
    import sqlite3
    conn = sqlite3.connect("shixiangzhi.db")
    conn.execute("DELETE FROM couplet WHERE word_a='测试甲' AND word_b='测试乙'")
    conn.commit(); conn.close()

    print("\n【问题3②】relations 仅保留共现 + CSV 导入")
    cooc_csv = ("name,to,cooccurrence_type,NPMI,diaphaneity,verse,description\n"
                "测试象,测试对,句内,0.5,0.6,测试共现句,测试说明\n")
    r = c.post("/api/admin/import?dry_run=false", files=[("files", ("g.csv", cooc_csv, "text/csv"))], headers=h)
    rep = r.json()["data"]["reports"][0]
    check("共现 CSV 识别并入库", rep["type"] == "cooccurrence" and rep["inserted"] == 1, str(rep))
    conn = sqlite3.connect("shixiangzhi.db")
    conn.execute("DELETE FROM cooccurrence_stat WHERE word_a='测试象' AND word_b='测试对'")
    conn.commit(); conn.close()
    # 关系类型固定为共现
    r = c.post("/api/admin/relation", headers=h, json={
        "from_concept_id": 1, "to_concept_id": 2, "relation_type": "对仗", "description": "x"})
    rid = r.json()["data"]["id"]
    conn = sqlite3.connect("shixiangzhi.db")
    rt = conn.execute("SELECT relation_type FROM concept_relation WHERE id=?", (rid,)).fetchone()[0]
    conn.execute("DELETE FROM concept_relation WHERE id=?", (rid,))
    conn.commit(); conn.close()
    check("关系类型强制为「共现」", rt == "共现", rt)

    print("\n【问题3③】共现知识图谱数据（线粗=NPMI/线型=类型/透明度=diaphaneity）")
    co = c.get("/api/concept/1/cooccurrence").json()["data"]
    check("返回中心节点+边", len(co["nodes"]) > 0 and len(co["edges"]) > 0)
    check("中心节点标记", any(n.get("center") for n in co["nodes"]))
    e = co["edges"][0]
    check("边含 npmi/type/diaphaneity/verse/description",
          all(k in e for k in ("npmi", "type", "diaphaneity", "verse", "description")))
    check("diaphaneity ≥ 0.2", all(x["diaphaneity"] >= 0.2 for x in co["edges"]))

    print("\n【问题4②③】艺术展厅（主朝代统计检索/封面兜底）")
    a = c.get("/api/artwork/list").json()["data"]
    check("dynasties 含朝代段+数量", all("name" in x and "count" in x for x in a["filters"]["dynasties"]),
          str(a["filters"]["dynasties"]))
    check("items 返回 dynasty_main", "dynasty_main" in a["items"][0])
    check("thumb 兜底 image_url", all(it["thumb_url"] for it in a["items"]))
    song = c.get("/api/artwork/list", params={"dynasty": "宋"}).json()["data"]
    check("按主朝代检索可用", song["total"] >= 0)

    print("\n【问题5】用法谱系 AI 总结接口")
    r = c.get("/api/concept/1/usage-summary")
    check("usage-summary 返回 text", bool(r.json()["data"].get("text")))

    print("\n【综合】全部端点无 500")
    endpoints = ["/api/concept/list", "/api/concept/1", "/api/concept/1/cooccurrence",
                 "/api/concept/1/usage-spectrum", "/api/artwork/list", "/api/concept/panorama"]
    ok = all(c.get(ep).status_code == 200 for ep in endpoints)
    check("关键端点均 200", ok)

print(f"\n════════════ 验收结果：通过 {PASS} 项，失败 {FAIL} 项 ════════════")
raise SystemExit(1 if FAIL else 0)
