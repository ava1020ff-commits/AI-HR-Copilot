"""可复现的能力模型证据评分；无 LLM 总分、无淘汰或候选人状态变更。"""

import re
from decimal import Decimal, ROUND_HALF_UP

from services.jd_parser import JDParseError, validate_job
from services.resume_parser import CONTACT, FIELDS, SENSITIVE

RULE_VERSION = "evidence-v1"
NO_EVIDENCE = "暂无明确证据"
RECOMMENDATIONS = ("建议进一步评估", "信息不足", "匹配度较低")
PRIVATE = re.compile(SENSITIVE.pattern + r"|婚育|生育|已育|未育|怀孕|孕期|\b(?:male|female|pregnan\w*|parental)\b", re.I)
NEGATIVE = re.compile(r"没有|暂无|未曾|未掌握|不会|不熟悉|不具备|缺乏|缺少|未参与|未使用|未负责|不了解|未做过|尚未|无.{0,12}经验|\b(?:no|not|never|without|lack\w*)\b", re.I)
TITLE = re.compile(r"职位|岗位|职称|担任|出任|工程师|经理|总监|分析师|负责人|专家|开发者|程序员|架构师|科学家|研究员|主管|助理|\b(?:title|role|engineer|manager|director|developer|analyst|consultant|architect|scientist|lead)\b", re.I)
# “开发/设计/分析/沟通”单独出现也可能只是岗位简称或技能名，不构成实践证据。
ACTION = re.compile(r"使用|运用|完成|实现|负责|主导|参与|搭建|交付|上线|协调|推动|\b(?:built|implemented|delivered|developed|used|led|designed|analyzed|collaborated)\b", re.I)
ALIASES = {
    "需求分析": ("需求分析", "需求调研", "requirements analysis"),
    "产品设计": ("产品设计", "原型设计", "product design"),
    "用户研究": ("用户研究", "用户访谈", "user research"),
    "大模型": ("大模型", "LLM", "large language model"),
    "RAG": ("RAG", "检索增强生成"),
    "机器学习": ("机器学习", "machine learning"),
    "项目交付": ("项目交付", "项目上线", "交付项目", "project delivery"),
    "数据分析": ("数据分析", "data analysis"),
    "沟通协作": ("沟通", "协作", "跨部门协调", "communication", "collaborated"),
    "Python": ("Python",), "SQL": ("SQL",), "REST API": ("REST API", "RESTful"),
    "Docker": ("Docker",), "Java": ("Java",), "JavaScript": ("JavaScript",),
}
DEFAULTS = {
    "产品": ["需求分析", "产品设计", "用户研究"],
    "AI": ["大模型", "RAG", "机器学习"],
    "人工智能": ["大模型", "RAG", "机器学习"],
    "项目": ["项目交付"],
    "数据": ["SQL", "数据分析"],
    "沟通": ["沟通协作"],
    "协作": ["沟通协作"],
    "后端": ["Python", "SQL", "REST API"],
}
DEGREES = {"大专": 1, "专科": 1, "本科": 2, "学士": 2, "硕士": 3, "博士": 4}


class MatchingError(ValueError):
    """可向 HR 展示的规则错误。"""


def contains(text: str, term: str) -> bool:
    if re.search(r"[a-zA-Z]", term):
        return bool(re.search(r"(?<![a-zA-Z0-9])" + re.escape(term) + r"(?![a-zA-Z0-9])", text, re.I))
    return term in text


def _model(job: dict) -> list[dict]:
    try:
        model = validate_job(job)["competency_model"]
    except JDParseError as exc:
        raise MatchingError(str(exc)) from None
    if not model:
        raise MatchingError("岗位尚无能力模型，请先完善 JD 的能力模型。")
    for item in model:
        if PRIVATE.search(item["dimension"] + " " + item["description"]):
            raise MatchingError("岗位能力模型包含敏感或歧视性指标，不能用于评分，请先修正。")
        if Decimal(str(item["weight"])).as_tuple().exponent < -2:
            raise MatchingError("岗位权重最多保留两位小数。")
    if sum(Decimal(str(item["weight"])) for item in model) != Decimal("100"):
        raise MatchingError("岗位能力模型权重必须精确合计 100，系统不会自动重分配权重。")
    return model


def build_rubric(job: dict) -> dict[str, list[str]]:
    """优先采用维度描述中的明确指标，通用维度提供可编辑的默认口径。"""
    rubric = {}
    for item in _model(job):
        name, description = item["dimension"], item["description"]
        if "教育" in name or "学历" in name:
            text = description + " " + job["education"]
            degrees = [degree for degree in DEGREES if degree in text]
            rubric[name] = [min(degrees, key=DEGREES.get)] if degrees else []
            continue
        explicit = [key for key, aliases in ALIASES.items() if any(contains(description, alias) for alias in aliases)]
        if explicit:
            rubric[name] = explicit
        else:
            rubric[name] = next((list(terms) for token, terms in DEFAULTS.items() if contains(name, token)), [])
    return rubric


def _evidence(term: str, candidate: dict) -> list[dict]:
    hits = []
    aliases = ALIASES.get(term, (term,))
    education = term in DEGREES
    for field in FIELDS:
        # 学历只从 education 读取；其他指标不从院校名称或证书名称推断技能。
        if education and field != "education":
            continue
        if not education and field not in ("skills", "work_experience", "internships", "projects"):
            continue
        values = candidate.get(field, [])
        if not isinstance(values, list):
            raise MatchingError("候选人职业字段格式有误，请重新确认简历。")
        for index, record in enumerate(values):
            if not isinstance(record, str):
                raise MatchingError("候选人职业字段必须为文本数组。")
            # 不引用含敏感片段的记录；原文和姓名不进入评分。
            if PRIVATE.search(record) or CONTACT.search(record):
                continue
            for raw in re.split(r"[。！？!?\n;；|/]+", record):
                quote = raw.strip()
                if not quote or NEGATIVE.search(quote) or TITLE.search(quote):
                    continue
                # 常见岗位简称，即使误放入 skills 也不能成为能力证据。
                if re.fullmatch(r"(?:高级|资深|初级|中级)?\s*(?:Python|Java|SQL|AI|RAG|前端|后端)\s*(?:开发|研发|设计|分析)", quote, re.I):
                    continue
                if education:
                    ranks = [rank for degree, rank in DEGREES.items() if degree in quote]
                    if not ranks or max(ranks) < DEGREES[term] or re.search(r"在读|肄业|未毕业|就读|攻读|studying|pursuing", quote, re.I):
                        continue
                    level, confidence = Decimal("1"), 0.8
                elif any(contains(quote, alias) for alias in aliases):
                    if field == "skills":
                        level, confidence = Decimal("0.5"), 0.5
                    elif ACTION.search(quote):
                        level, confidence = Decimal("1"), 0.8
                    else:
                        continue
                else:
                    continue
                hits.append({"source": f"{field}[{index}]", "quote": quote, "level": level, "confidence": confidence})
    return hits


def calculate_match(job: dict, candidate: dict, rubric: dict[str, list[str]] | None = None) -> dict:
    model = _model(job)
    rubric = build_rubric(job) if rubric is None else rubric
    if set(rubric) != {item["dimension"] for item in model}:
        raise MatchingError("评分指标必须与岗位模型维度完全对应。")
    dimensions, strengths, risks, questions = [], [], [], []
    supported_weight = Decimal("0")
    for item in model:
        name, maximum = item["dimension"], Decimal(str(item["weight"]))
        terms = rubric[name]
        if not isinstance(terms, list) or len(terms) > 20 or any(not isinstance(term, str) or not term.strip() or len(term) > 80 for term in terms):
            raise MatchingError("每个维度最多 20 个非空评分指标，每条不超过 80 字符。")
        terms = list(dict.fromkeys(term.strip() for term in terms))
        if any(PRIVATE.search(term) or CONTACT.search(term) for term in terms):
            raise MatchingError("评分指标不得包含年龄、性别、婚育等敏感信息。")
        levels, quotes, sources, confidences, missing, details = [], [], [], [], [], []
        for term in terms:
            hits = _evidence(term, candidate)
            best = max(hits, key=lambda hit: hit["level"], default=None)
            level = best["level"] if best else Decimal("0")
            levels.append(level)
            confidences.append(best["confidence"] if best else 0)
            details.append({
                "criterion": term, "attainment": float(level),
                "evidence_sources": [{"source": best["source"], "quote": best["quote"]}] if best else [],
            })
            if best:
                if best["quote"] not in quotes:
                    quotes.append(best["quote"])
                    sources.append({"source": best["source"], "quote": best["quote"]})
            else:
                missing.append(term)
        ratio = sum(levels) / len(terms) if terms else Decimal("0")
        score = (maximum * ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if maximum > 0 and terms:
            supported_weight += maximum * Decimal(sum(value > 0 for value in levels)) / len(terms)
        reason = f"{len(terms)} 个指标等分权重；实践/学历证据=1，技能自述=0.5，无证据=0；{maximum} × {float(ratio):.4f} = {score}。" if terms else "没有可执行评分指标，暂不计分；请 HR 补充明确口径。"
        dimensions.append({
            "dimension": name, "requirement": item["description"], "score": float(score), "max_score": float(maximum),
            "evidence": quotes if quotes else [NO_EVIDENCE], "evidence_sources": sources,
            "reason": reason, "confidence": round(sum(confidences) / len(terms), 2) if terms else 0,
            "criteria": details,
        })
        if maximum <= 0:
            continue
        if ratio >= Decimal("0.75"):
            strengths.append(f"{name}：简历证据覆盖较充分（{score}/{maximum}），仍需核实实际水平。")
        if missing or not terms:
            risks.append((f"【材料未提及】{name}：当前规则未找到明确支持证据：" + "、".join(missing) + "；请复核原文，未识别不等于未提及，更不代表不具备能力。") if terms else f"【口径待明确】{name}：请先明确评分指标，不对候选人能力作判断。")
            questions.append(f"请围绕{name}补充具体案例、个人贡献和可核验成果" + (f"，重点核实：{'、'.join(missing)}。" if missing else "，并先明确评价指标。"))
        if any(value == Decimal("0.5") for value in levels):
            risks.append(f"【仅技能自述】{name}：尚缺实践佐证，请补充具体项目、个人贡献与产出。")
            questions.append(f"请展示{name}相关的实际产出，并说明本人承担的工作。")
    total = sum(Decimal(str(dimension["score"])) for dimension in dimensions)
    coverage = round(float(supported_weight), 2)
    recommendation = "信息不足" if supported_weight < 60 else "建议进一步评估" if total >= 60 else "匹配度较低"
    if not questions:
        questions.append("请核实上述经历的真实性、个人贡献及成果，不能仅凭简历描述作出录用决定。")
    return {
        "dimensions": dimensions, "total_score": float(total), "strengths": strengths,
        "risks": risks, "questions_to_verify": questions, "recommendation": recommendation,
        "evidence_coverage": coverage, "rule_version": RULE_VERSION,
        "notice": "分数是当前简历的证据覆盖分，不是实际能力或录用概率；仅辅助人工评估，禁止自动淘汰。",
    }
