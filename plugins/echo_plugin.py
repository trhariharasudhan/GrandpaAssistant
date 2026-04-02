name = "echo"
description = "Returns the input exactly as received."


def execute(input_data):
    return {
        "ok": True,
        "plugin": name,
        "result": input_data,
    }
