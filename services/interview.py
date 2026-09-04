"""基于可追溯上下文生成面试提纲；不调用外部模型，不作录用决定。"""

import re

from services.matching import PRIVATE, MatchingError, calculate_match, contains
from services.resume_parser import CONTACT, FIELDS

CATEGORIES = ("经历真实性验证", "STAR行为面试", "专业能力", "风险验证")
DETAILS = {
    "RAG": ("检索召回、分块和重排分别如何评估？如何区分检索失败与生成错误？", "能给出检索评测样本、召回指标和错误归因", "只描述调用模型，无法说明检索质量如何验证"),
    "SQL": ("如何处理重复记录、NULL 和一对多关联？如何用执行计划验证性能？", "能解释数据粒度、边界样例及执行计划", "无法解释关联后指标膨胀或查询验证过程"),
    "需求分析": ("需求来自哪些用户证据？冲突需求如何排序，验收标准如何确定？", "能连接用户证据、取舍依据与验收标准", "只罗列需求，无法解释优先级和验证依据"),
    "产品设计": ("你如何比较替代方案？原型测试中的发现如何改变设计？", "能展示方案比较及用户反馈导致的迭代", "只讲界面方案，无法说明设计依据"),
    "数据分析": ("指标口径、对照组与潜在混杂因素如何处理？", "能区分相关和因果，说明口径与验证方法", "只有结论，缺少可复核的数据口径"),
    "Python": ("如何设计异常处理和测试边界？请用一段伪代码解释核心实现。", "能解释实现边界、异常路径及测试方法", "无法把方案落实到可解释的实现步骤"),
    "沟通协作": ("哪一次分歧影响了交付？各方诉求、你的协调动作和最终约定是什么？", "能区分各方诉求与自己的沟通行动", "把团队成果完全归于个人，无法解释分歧处理"),
    "项目交付": ("验收范围、交付风险和上线后的验证如何安排？", "能说明验收标准、交付责任和结果验证", "无法说明交付完成的判断依据"),
}


class InterviewError(ValueError):
    """输入不足或报告与上下文不一致。"""


def _safe(text: object) -> bool:
    return isinstance(text, str) and bool(text.strip()) and not PRIVATE.search(text) and not CONTACT.search(text)


def _anchors(candidate: dict) -> list[dict]:
    result = []
    for field in ("projects", "work_experience", "internships", "education", "skills", "certificates"):
        values = candidate.get(field, [])
        if not isinstance(values, list):
            raise InterviewError("候选人字段格式错误，请先重新确认简历。")
        for index, text in enumerate(values):
            if _safe(text):
                result.append({"source": f"{field}[{index}]", "quote": text, "field": field})
    return result


def _report(job: dict, candidate: dict, report: dict) -> dict:
    try:
        rubric = {item["dimension"]: [criterion["criterion"] for criterion in item["criteria"]] for item in report["dimensions"]}
        verified = calculate_match(job, candidate, rubric)
        if verified != report:
            raise InterviewError("匹配报告与当前岗位、候选人或规则不一致，请重新计算匹配。")
        return verified
    except MatchingError as exc:
        raise InterviewError(str(exc)) from None
    except (KeyError, TypeError, AttributeError):
        raise InterviewError("匹配报告格式错误，请重新计算匹配。") from None


def generate_interview(job: dict, jd: str, candidate: dict, report: dict) -> dict:
    """所有问题必须包含真实简历引用和岗位要求；报告必须可重算验证。"""
    report = _report(job, candidate, report)
    anchors = _anchors(candidate)
    if not anchors:
        raise InterviewError("简历没有可引用的职业信息，无法生成针对性问题，请先补充简历。")
    jd_lines = [line.strip() for line in re.split(r"[\n\r；;。]+", jd) if _safe(line)]
    if not jd_lines:
        raise InterviewError("JD 没有可用的职业要求，请先补充或清理 JD。")
    dimensions = sorted((item for item in report["dimensions"] if item["max_score"] > 0), key=lambda item: -item["max_score"])
    model = {item["dimension"]: item for item in job["competency_model"]}
    groups = {category: [] for category in CATEGORIES}
    omissions = []
    used = set()

    def context(dimension: dict, career_only: bool = False) -> tuple[dict, str, str, str] | None:
        terms = [item["criterion"] for item in dimension["criteria"]]
        candidates = [item for item in anchors if not career_only or item["field"] in ("projects", "work_experience", "internships")]
        if not candidates:
            return None
        report_sources = {item["source"] for item in dimension["evidence_sources"]}
        anchor = max(candidates, key=lambda item: (
            item["source"] in report_sources,
            sum(contains(item["quote"], term) for term in terms),
            item["source"] not in used,
            item["field"] in ("projects", "work_experience", "internships"),
        ))
        used.add(anchor["source"])
        requirement = model[dimension["dimension"]]["description"]
        jd_quote = max(jd_lines, key=lambda line: (sum(contains(line, term) for term in terms), len(line)))
        target = "、".join(terms) if terms else requirement
        return anchor, requirement, jd_quote, target

    def add(category: str, dimension: dict, ctx: tuple, question: str, purpose: str, follow: list[str], good: list[str], risk: list[str]) -> None:
        anchor, requirement, jd_quote, target = ctx
        groups[category].append({
            "question": question, "purpose": purpose, "evaluation_dimension": dimension["dimension"],
            "follow_up": follow, "good_signals": good, "risk_signals": risk,
            "sources": {"resume": {"source": anchor["source"], "quote": anchor["quote"]}, "jd": jd_quote, "competency_description": requirement},
            "matching_context": {"score": dimension["score"], "max_score": dimension["max_score"], "confidence": dimension["confidence"], "criteria": dimension["criteria"]},
        })

    for dimension in dimensions[:2]:
        ctx = context(dimension, career_only=True)
        if ctx is None:
            continue
        anchor, requirement, jd_quote, target = ctx
        quoted = f"简历写到「{anchor['quote']}」"
        add("经历真实性验证", dimension, ctx,
            f"{quoted}。针对岗位「{requirement}」的要求，请还原这段经历中你亲自承担的工作、交付物和可核验的过程，哪些是团队或他人完成的？",
            f"核实这条简历记录对「{dimension['dimension']}」的证据支撑，而不是根据职位名称推断能力。",
            [f"围绕「{target}」，请按发生顺序说明你做过的关键动作。", "可否口述或展示不含前雇主机密的脱敏产出？若不能展示，可描述验证方法。"],
            [f"能将「{anchor['quote']}」拆分为个人贡献和团队贡献", "能提供时间顺序一致、可复核且不涉及机密的过程细节"],
            ["关键动作与交付物反复矛盾，需进一步澄清", "只重复职位名称，不能说明个人贡献；不能提供保密材料本身不算负面信号"])
        add("STAR行为面试", dimension, ctx,
            f"围绕简历中的「{anchor['quote']}」，请选一次与「{target}」直接相关的真实挑战，按 S（情境）、T（任务）、A（你采取的行动）、R（结果）讲述；若当时未涉及该能力，请明确说明。",
            f"结合 JD「{jd_quote}」，核实「{dimension['dimension']}」在真实约束下的行为证据。",
            [f"在该经历中，围绕「{target}」最关键的限制和你需要负责的目标是什么？", "你比较过什么替代做法？结果如何验证，哪些变化不能归因于你的行动？"],
            [f"能把「{target}」对应到具体任务、行动和结果", "能区分事实、个人判断和不可归因因素"],
            ["只有团队叙事，无法解释本人行动", "无法说明结果的验证方式；未经历过该场景应记录为信息缺口"])
    if not groups["经历真实性验证"]:
        omissions.append("简历没有可引用的项目、工作或实习记录，未生成经历真实性及 STAR 问题；请先补充经历，不虚构情境。")

    for dimension in dimensions[:3]:
        ctx = context(dimension)
        anchor, requirement, jd_quote, target = ctx
        detail = next((value for key, value in DETAILS.items() if contains(target, key)), None)
        follow = detail[0] if detail else f"针对「{target}」，请解释判断标准、方案边界及验证步骤。"
        practice = anchor["source"] in {item["source"] for item in dimension["evidence_sources"]}
        boundary = "请说明实际做法" if practice else "这条记录尚不能证明该项能力；如无实际经验，请明确标注以下为假设方案"
        add("专业能力", dimension, ctx,
            f"简历记录「{anchor['quote']}」；JD 提出「{jd_quote}」，能力模型要求「{requirement}」。围绕「{target}」，{boundary}：{follow}",
            f"核实「{target}」的方法与边界，区分实践事实和现场推演，不将简历提及视为熟练掌握。",
            [follow, f"与「{anchor['quote']}」相比，满足该岗位要求还缺哪些条件？哪些结论需要验证？"],
            [detail[1] if detail else f"能为「{target}」提出可检验的标准", "清晰标注实际经历与假设，不夸大熟练程度"],
            [detail[2] if detail else f"对「{target}」只给结论，无法说明验证步骤", "将假设方案说成既往成果，需进一步核实"])

    priority = sorted(dimensions, key=lambda item: (item["score"] / item["max_score"], item["confidence"], -item["max_score"]))
    for dimension in priority[:2]:
        ctx = context(dimension)
        anchor, requirement, jd_quote, target = ctx
        missing = [item["criterion"] for item in dimension["criteria"] if item["attainment"] == 0]
        partial = [item["criterion"] for item in dimension["criteria"] if item["attainment"] == 0.5]
        gap = "暂无明确证据支持「" + "、".join(missing) + "」" if missing else "「" + "、".join(partial) + "」仅有技能自述" if partial else "已有描述仍需核验适用范围和真实性"
        if not dimension["criteria"]:
            gap = "评分指标尚未明确，报告无法评价该维度"
        add("风险验证", dimension, ctx,
            f"匹配报告对「{dimension['dimension']}」记录：{gap}。简历可定位的记录是「{anchor['quote']}」。针对岗位「{requirement}」，是否有可补充的相关案例？如果没有，请说明尚未接触的部分，避免把推演当作经历。",
            f"核实「{dimension['dimension']}」的信息缺口或证据边界，不将匹配分数作为能力或诚信结论。",
            [f"请区分「{target}」中亲自实践、仅了解和未接触的内容。", f"结合 JD「{jd_quote}」，哪些任务需要支持或进一步验证？"],
            ["主动区分已验证事实、知识自述及未接触内容", f"能为「{target}」提供补充证据或可验证的学习方案"],
            ["补充描述与先前证据矛盾且无法澄清", "将没有证据误说成已完成；单纯缺少经验不代表诚信问题"])
    return {"categories": groups, "omissions": omissions, "generator": "grounded-rules-v1", "notice": "问题用于人工核实，不自动评价回答或作出录用、淘汰决定。不得要求候选人泄露商业秘密。"}
