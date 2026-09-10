"""BOSS 沟通话术生成与页面回归测试，不访问真实模型。"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from streamlit.testing.v1 import AppTest

from services.boss_messaging import (
    BossMessageError,
    MISSING_COMPENSATION,
    SYSTEM_PROMPT,
    clean_json_content,
    generate_boss_message,
    validate_boss_message,
)
from services.jd_parser import LLMConfig

PAGE = Path(__file__).resolve().parents[1] / "pages" / "08_BOSS沟通话术.py"
JD = "产品运营岗位，负责用户运营、活动策划、数据分析，并与产品和市场团队协作。薪资15-20K，双休、五险一金和餐补。"
GREETING = "你好～我们正在招聘产品运营，岗位方向和你的求职方向可能比较匹配，想先和你简单聊聊，近期方便了解一下新机会吗？"
RESULT = {
    "greeting": GREETING,
    "job_description": "工作会围绕用户运营、活动策划和数据分析展开，也会与产品、市场团队配合推进项目。",
    "salary_benefits": "薪资范围是15-20K，双休、五险一金，另外有餐补，具体可以进一步沟通。",
    "full_message": GREETING + " 工作会围绕用户运营、活动策划和数据分析展开，也会与产品、市场团队配合推进项目。薪资范围是15-20K，双休、五险一金，另外有餐补，具体可以进一步沟通。",
}


def response_for(content: str, status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.json.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": content}}]}
    return response


def test_prompt_is_dedicated_and_forbids_invention() -> None:
    assert "BOSS 直聘" in SYSTEM_PROMPT
    assert "不得虚构" in SYSTEM_PROMPT
    assert "JD中暂未注明" in SYSTEM_PROMPT


def test_markdown_json_is_cleaned_and_validated() -> None:
    content = "```json\n" + json.dumps(RESULT, ensure_ascii=False) + "\n```"
    assert json.loads(clean_json_content(content)) == RESULT
    assert validate_boss_message(RESULT, JD) == RESULT


def test_missing_compensation_requires_explicit_message() -> None:
    no_pay_jd = "产品运营岗位，负责用户运营、活动策划和数据分析，并与产品及市场团队协作推进项目。"
    result = dict(RESULT, salary_benefits=MISSING_COMPENSATION)
    result["full_message"] = GREETING + " 工作负责用户运营、活动策划和数据分析。" + MISSING_COMPENSATION
    assert validate_boss_message(result, no_pay_jd)["salary_benefits"] == MISSING_COMPENSATION
    with pytest.raises(BossMessageError, match="不一致"):
        validate_boss_message(dict(result, salary_benefits="薪资15-20K，双休。"), no_pay_jd)


def test_unlisted_benefit_is_rejected() -> None:
    with pytest.raises(BossMessageError, match="不一致"):
        validate_boss_message(dict(RESULT, salary_benefits=RESULT["salary_benefits"] + "另有住房补贴。"), JD)
    with pytest.raises(BossMessageError, match="不一致"):
        validate_boss_message(dict(RESULT, full_message=RESULT["full_message"] + "另有年终奖。"), JD)
    with pytest.raises(BossMessageError, match="不一致"):
        validate_boss_message(dict(RESULT, salary_benefits="薪资范围是20-30K，双休、五险一金和餐补。"), JD)


def test_request_contract_and_code_fence(monkeypatch) -> None:
    post = MagicMock(return_value=response_for("```json\n" + json.dumps(RESULT, ensure_ascii=False) + "\n```"))
    monkeypatch.setattr("services.boss_messaging.requests.post", post)
    config = LLMConfig("test-key", "https://example.invalid/v1", "test-model")
    assert generate_boss_message(JD, config) == RESULT
    request = post.call_args.kwargs
    assert request["json"]["messages"][0]["content"] == SYSTEM_PROMPT
    assert request["json"]["messages"][1]["content"] == JD
    assert request["json"]["response_format"] == {"type": "json_object"}
    assert request["allow_redirects"] is False


@pytest.mark.parametrize("error", [requests.Timeout("private"), requests.ConnectionError("private")])
def test_api_failure_is_redacted(monkeypatch, error) -> None:
    monkeypatch.setattr("services.boss_messaging.requests.post", MagicMock(side_effect=error))
    with pytest.raises(BossMessageError, match="生成失败") as captured:
        generate_boss_message(JD, LLMConfig("test-key", "https://example.invalid/v1", "test-model"))
    assert "private" not in str(captured.value)


def test_page_opens_and_validates_empty_input(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setattr("streamlit.page_link", MagicMock())
    app = AppTest.from_file(str(PAGE)).run(timeout=15)
    assert not app.exception
    assert app.title[0].value == "BOSS沟通话术生成"
    assert app.text_area[0].placeholder.startswith("请粘贴岗位JD")
    app.button[0].click().run(timeout=15)
    assert app.warning[0].value == "请先输入岗位JD"


def test_page_validates_short_input(monkeypatch) -> None:
    monkeypatch.setattr("streamlit.page_link", MagicMock())
    app = AppTest.from_file(str(PAGE)).run(timeout=15)
    app.text_area[0].input("产品运营")
    app.button[0].click().run(timeout=15)
    assert "JD信息较少" in app.warning[0].value


def test_page_renders_all_four_result_cards(monkeypatch) -> None:
    monkeypatch.setattr("streamlit.page_link", MagicMock())
    app = AppTest.from_file(str(PAGE))
    app.session_state["boss_message_result"] = RESULT
    app.run(timeout=15)
    assert not app.exception
    markdown = [item.value for item in app.markdown]
    assert any("打招呼语" in value for value in markdown)
    assert any("工作内容" in value for value in markdown)
    assert any("薪资福利" in value for value in markdown)
    assert any("完整沟通话术" in value for value in markdown)
