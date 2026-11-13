from rashi.model_table import free_chat_models, to_markdown


def test_free_chat_models_filters_and_marks_tools():
    data = {"data": [
        {"id": "paid-1", "endpoints": ["chat"], "pricing": {"free": False}},
        {"id": "free-chat", "endpoints": ["chat"], "pricing": {"free": True},
         "context_length": 1000, "tool_call": True, "reasoning": False},
        {"id": "free-image", "endpoints": ["image"], "pricing": {"free": True}},
    ]}
    models = free_chat_models(data)
    assert models == [{"id": "free-chat", "tools": True, "reasoning": False, "context": 1000}]
    assert "| free-chat | yes | no | 1,000 |" in to_markdown(models, "test")
