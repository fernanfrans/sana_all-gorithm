def translate_role(role: str) -> str:
    return "assistant" if role == "model" else role
