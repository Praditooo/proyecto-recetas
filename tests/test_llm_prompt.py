from app.services.llm_service import build_messages

INVENTORY = [
    {"name": "arroz", "quantity": 500, "unit": "g"},
    {"name": "huevo", "quantity": 4, "unit": "unidad"},
]


def test_prompt_includes_every_ingredient_with_quantity():
    user_message = build_messages(INVENTORY)[1]["content"]
    assert "arroz: 500 g" in user_message
    assert "huevo: 4 unidad" in user_message


def test_system_prompt_requires_json_only():
    system_message = build_messages(INVENTORY)[0]
    assert system_message["role"] == "system"
    assert "JSON" in system_message["content"]
    assert "estimated_minutes" in system_message["content"]
