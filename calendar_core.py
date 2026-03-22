import datetime
import calendar
import re

# ================= BASIC DATE =================


def now():
    return datetime.datetime.now()


def get_date():
    return now().strftime("%d-%m-%Y")


def get_time():
    return now().strftime("%I:%M %p")


def get_period():
    h = now().hour
    if h < 12:
        return "It is Morning"
    elif h < 15:
        return "It is Afternoon"
    elif h < 19:
        return "It is Evening"
    return "It is Night"


# ================= ORDINAL FORMATTER =================


def ordinal(n):
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n % 10]}"


# ================= RELATIVE DATE BASE =================


def get_relative_base(user_input):
    user_input = user_input.lower()
    today = now().date()
    if "today" in user_input:
        return today
    if "yesterday" in user_input:
        return today - datetime.timedelta(days=1)
    if "tomorrow" in user_input:
        return today + datetime.timedelta(days=1)
    if "last week" in user_input:
        return today - datetime.timedelta(weeks=1)
    if "next week" in user_input:
        return today + datetime.timedelta(weeks=1)
    if "last year" in user_input:
        return datetime.date(today.year - 1, today.month, today.day)
    if "next year" in user_input:
        return datetime.date(today.year + 1, today.month, today.day)
    if "last month" in user_input:
        month = today.month - 1 or 12
        year = today.year - 1 if today.month == 1 else today.year
        day = min(today.day, calendar.monthrange(year, month)[1])
        return datetime.date(year, month, day)
    if "next month" in user_input:
        month = today.month + 1 if today.month < 12 else 1
        year = today.year + 1 if today.month == 12 else today.year
        day = min(today.day, calendar.monthrange(year, month)[1])
        return datetime.date(year, month, day)
    return None


# ================= OFFSET HANDLER =================


def handle_offsets(user_input):
    user_input = user_input.lower()
    pattern = (
        r"(\d+)\s+(day|days|week|weeks)\s+(after|before|later)|"
        r"(after|before)\s+(\d+)\s+(day|days|week|weeks)"
    )
    match = re.search(pattern, user_input)
    if not match:
        return None
    groups = match.groups()
    if groups[0]:  # 5 days after
        amount = int(groups[0])
        unit = groups[1]
        direction = groups[2]
    else:  # after 5 days
        direction = groups[3]
        amount = int(groups[4])
        unit = groups[5]
    if direction == "later":
        direction = "after"
    base_date = get_relative_base(user_input) or extract_specific_date(user_input)
    if base_date is None:
        base_date = now().date()
    delta = (
        datetime.timedelta(weeks=amount)
        if "week" in unit
        else datetime.timedelta(days=amount)
    )
    return base_date + delta if direction == "after" else base_date - delta


# ================= DATE DIFFERENCE =================


def handle_difference(user_input):
    if "between" not in user_input.lower():
        return None
    dates = re.findall(r"\d{1,2}\s+[a-zA-Z]+\s+\d{4}", user_input)
    if len(dates) != 2:
        return None
    d1 = extract_specific_date(dates[0])
    d2 = extract_specific_date(dates[1])
    if d1 and d2:
        diff = abs((d2 - d1).days)
        return f"There are {diff} days between {d1} and {d2}."
    return None


# ================= DATE INFO GENERATOR =================


def generate_full_info(date_obj):
    return (
        f"The date is {date_obj.strftime('%A')}, "
        f"{ordinal(date_obj.day)} {date_obj.strftime('%B')} {date_obj.year}. "
        f"It falls in week number {date_obj.isocalendar()[1]} of the year."
    )


# ================= SPECIFIC DATE PARSER =================


def extract_specific_date(text):
    text = text.lower()
    for i in range(1, 13):
        month_name = calendar.month_name[i].lower()
        text = text.replace(month_name, str(i))
    numbers = list(map(int, re.findall(r"\d+", text)))
    if len(numbers) >= 3:
        if numbers[0] > 31:
            year, month, day = numbers[:3]
        else:
            day, month, year = numbers[:3]
        try:
            return datetime.date(year, month, day)
        except ValueError:
            return None
    return None


# ================= CALENDAR DISPLAY =================


def show_month(year, month):
    cal = calendar.month(year, month)
    print(cal)


def show_year(year):
    cal = calendar.TextCalendar().formatyear(year)
    print(cal)


# ================= CALENDAR QUERY HANDLER =================


def handle_calendar_queries(command, speak):
    command = command.lower()
    now_dt = now()

    if "leap year" in command:
        year = now_dt.year
        numbers = re.findall(r"\d{4}", command)
        if numbers:
            year = int(numbers[0])
        elif "next year" in command:
            year += 1
        elif "last year" in command:
            year -= 1
        result = "is" if calendar.isleap(year) else "is not"
        speak(f"{year} {result} a leap year.")
        return True

    if re.search(r"\d{1,2}\s+\d{1,2}\s+\d{4}|\d{1,2}\s+[a-zA-Z]+\s+\d{4}", command):
        date_obj = extract_specific_date(command)
        if date_obj:
            speak(generate_full_info(date_obj))
            return True

    if "month" in command:
        numbers = re.findall(r"\d{4}", command)
        year = int(numbers[0]) if numbers else now_dt.year
        month_match = re.search(
            r"(january|february|march|april|may|june|july|august|september|october|november|december)",
            command,
        )
        month = now_dt.month
        if month_match:
            month = list(calendar.month_name).index(month_match.group(1).capitalize())
        speak(f"Here is the calendar for {calendar.month_name[month]} {year}:")
        show_month(year, month)
        return True

    if "calendar" in command:
        numbers = re.findall(r"\d{4}", command)
        year = int(numbers[0]) if numbers else now_dt.year
        speak(f"Here is the calendar for {year}:")
        show_year(year)
        return True

    if "week" in command:
        week_number = now_dt.isocalendar()[1]
        speak(f"This is week number {week_number}.")
        return True

    if "days left" in command and "month" in command:
        total_days = calendar.monthrange(now_dt.year, now_dt.month)[1]
        remaining = total_days - now_dt.day
        speak(f"There are {remaining} days left in this month.")
        return True

    if "weeks left" in command and "year" in command:
        current_week = now_dt.isocalendar()[1]
        total_weeks = datetime.date(now_dt.year, 12, 28).isocalendar()[1]
        remaining = total_weeks - current_week
        speak(f"There are {remaining} weeks left in this year.")
        return True

    return False
