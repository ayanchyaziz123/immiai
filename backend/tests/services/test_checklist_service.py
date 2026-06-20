from app.services.checklist_service import ChecklistService


def test_get_known_checklist():
    svc = ChecklistService()
    result = svc.get_checklist("h-1b")
    assert result.visa_type == "h-1b"
    assert len(result.items) > 0
    required = [i for i in result.items if i.required]
    assert len(required) > 0


def test_get_checklist_case_insensitive():
    svc = ChecklistService()
    result = svc.get_checklist("H-1B")
    assert len(result.items) > 0


def test_get_unknown_checklist_returns_fallback():
    svc = ChecklistService()
    result = svc.get_checklist("unknown-visa-xyz")
    assert len(result.items) > 0


def test_list_types():
    svc = ChecklistService()
    types = svc.list_types()
    assert "h-1b" in types
    assert "asylum" in types
    assert "citizenship" in types
