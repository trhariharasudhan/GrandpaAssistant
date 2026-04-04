from iot_control import execute_iot_control, get_iot_action_history, resolve_iot_control_command


def dispatch_iot_command(command_text, confirm=False):
    result = execute_iot_control(command_text, confirm=confirm)
    return result.get("ok", False), result.get("message", "Smart Home command failed.")


def resolve_iot_command(command_text):
    return resolve_iot_control_command(command_text)


def run_iot_command(command_text, confirm=False):
    return execute_iot_control(command_text, confirm=confirm)


def recent_iot_actions(limit=10):
    return get_iot_action_history(limit=limit)
