from auctelis.build import build_all, check_schema_parity


def test_build_all_succeeds():
    result = build_all()
    assert result["status"] == "ok"


def test_schema_parity():
    check_schema_parity()
