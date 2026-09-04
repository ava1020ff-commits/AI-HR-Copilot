"""Cloud configuration tests use synthetic values only."""

import pytest

from database.dashboard import _connect
from database.jobs import get_candidate_db_path, get_db_path
from services import config
from services.jd_parser import LLMConfig


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    for name in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL", "JD_DATABASE_PATH", "RESUME_DATABASE_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config.st, "secrets", {})


def test_secrets_and_environment_precedence(monkeypatch):
    monkeypatch.setattr(config.st, "secrets", {"LLM_API_KEY": "test-only-key", "LLM_MODEL": "test-model"})
    assert LLMConfig.from_env().model == "test-model"
    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setenv("LLM_API_KEY", "")
    assert LLMConfig.from_env().model == "env-model"
    assert LLMConfig.from_env().api_key == ""


def test_missing_secrets_is_optional(monkeypatch):
    class MissingSecrets:
        def get(self, *args):
            raise FileNotFoundError

    monkeypatch.setattr(config.st, "secrets", MissingSecrets())
    assert LLMConfig.from_env().api_key == ""
    assert get_db_path() == config.PROJECT_ROOT / "database/recruitment.sqlite3"


def test_relative_paths_ignore_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JD_DATABASE_PATH", "data/jobs.sqlite3")
    assert get_db_path() == config.PROJECT_ROOT / "data/jobs.sqlite3"
    assert get_candidate_db_path() == get_db_path()
    monkeypatch.setattr(config.st, "secrets", {"RESUME_DATABASE_PATH": "data/resumes.sqlite3"})
    assert get_candidate_db_path() == config.PROJECT_ROOT / "data/resumes.sqlite3"


def test_nested_database_directory_created(tmp_path):
    path = tmp_path / "nested" / "data.sqlite3"
    connection = _connect(path)
    connection.close()
    assert path.is_file()


def test_bad_config_does_not_disclose_value(monkeypatch):
    monkeypatch.setattr(config.st, "secrets", {"LLM_API_KEY": {"private": "test-only-value"}})
    with pytest.raises(ValueError, match="配置 LLM_API_KEY 必须为字符串") as error:
        LLMConfig.from_env()
    assert "test-only-value" not in str(error.value)
