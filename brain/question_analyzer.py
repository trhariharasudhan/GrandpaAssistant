PERSONAL_KEYWORDS = [
    "my",
    "mine",
    "am i",
    "who am i",
    "my father",
    "my mother",
    "my email",
    "my phone",
    "my number",
    "my friend",
    "my family",
    "my city",
    "my location",
    "my address",
    "my birthday",
    "my age",
    "my skill",
    "my goal",
    "my goals",
    "my dream",
    "my routine",
    "my wake up time",
    "my sleep time",
    "my job",
    "my company",
    "my github",
    "my instagram",
    "my linkedin",
    "my twitter",
    "my favorite",
    "my book",
    "my series",
    "my browser",
    "my app"
]


def is_personal_question(question: str) -> bool:

    question = question.lower()

    for keyword in PERSONAL_KEYWORDS:
        if keyword in question:
            return True

    return False
