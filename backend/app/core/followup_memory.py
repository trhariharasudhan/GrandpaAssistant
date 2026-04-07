_last_context = {
    "selected_text": "",
    "last_result": "",
    "last_user_input": "",
    "last_interaction_id": "",
}


def set_selected_text(text):
    _last_context["selected_text"] = (text or "").strip()


def get_selected_text():
    return (_last_context.get("selected_text") or "").strip()


def set_last_result(text):
    _last_context["last_result"] = (text or "").strip()


def get_last_result():
    return (_last_context.get("last_result") or "").strip()


def set_last_user_input(text):
    _last_context["last_user_input"] = (text or "").strip()


def get_last_user_input():
    return (_last_context.get("last_user_input") or "").strip()


def set_last_interaction_id(value):
    _last_context["last_interaction_id"] = (value or "").strip()


def get_last_interaction_id():
    return (_last_context.get("last_interaction_id") or "").strip()


def get_best_followup_text():
    return get_selected_text() or get_last_result()
