"""人力基础数据持久化测试。"""

from database.hr_base_data import load_base_data, save_base_data


def test_base_data_round_trip_and_atomic_update(tmp_path) -> None:
    path = tmp_path / "hr.sqlite3"
    datasets = {
        "active": [{"员工编号": "1", "姓名": "甲"}],
        "departed": [{"员工编号": "2", "姓名": "乙"}],
        "hc": [{"二级部门": "业务部", "月初HC": "2"}],
    }
    save_base_data(datasets, path)
    loaded = load_base_data(path)
    assert loaded["active"] == datasets["active"]
    assert loaded["departed"] == datasets["departed"]
    assert loaded["hc"] == datasets["hc"]
    assert loaded["updated_at"]


def test_missing_base_data_is_safe(tmp_path) -> None:
    loaded = load_base_data(tmp_path / "missing.sqlite3")
    assert loaded == {"active": [], "departed": [], "hc": [], "updated_at": None}
