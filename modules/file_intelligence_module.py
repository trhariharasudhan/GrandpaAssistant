import os
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


SEARCH_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".pdf",
    ".docx",
    ".xlsx",
    ".pptx",
    ".jpg",
    ".jpeg",
    ".png",
}


def _search_roots():
    home = Path.home()
    onedrive = home / "OneDrive"
    roots = [
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        onedrive / "Desktop",
        onedrive / "Documents",
    ]
    return [root for root in roots if root.exists()]


def _iter_candidate_files(limit=500):
    count = 0
    for root in _search_roots():
        try:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in SEARCH_EXTENSIONS:
                    continue
                yield path
                count += 1
                if count >= limit:
                    return
        except Exception:
            continue


def _find_files(query, limit=5):
    query = query.lower().strip()
    if not query:
        return []

    matches = []
    for path in _iter_candidate_files():
        if query in path.name.lower():
            matches.append(path)
        if len(matches) >= limit:
            break
    return matches


def find_file(command):
    query = command
    prefixes = [
        "find file",
        "search file",
        "locate file",
    ]

    for prefix in prefixes:
        if command.startswith(prefix):
            query = command.replace(prefix, "", 1)
            break

    query = query.strip(" :")
    if not query:
        return "Tell me the file name you want to find."

    matches = _find_files(query)
    if not matches:
        return f"I could not find a file matching {query}."

    items = [str(path) for path in matches]
    return "Matching files: " + " | ".join(items)


def open_found_file(command):
    query = command.replace("open file named", "", 1).replace("open found file", "", 1).strip(" :")
    if not query:
        return "Tell me the file name you want to open."

    matches = _find_files(query, limit=1)
    if not matches:
        return f"I could not find a file named {query}."

    path = matches[0]
    try:
        os.startfile(str(path))
        return f"Opening file {path.name}."
    except Exception:
        return "I found the file, but I could not open it."


def recent_files():
    files = sorted(
        list(_iter_candidate_files()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not files:
        return "I could not find any recent files."

    lines = [f"{path.name}" for path in files[:5]]
    return "Recent files: " + " | ".join(lines)


def _read_pdf_preview(path):
    if PdfReader is None:
        return None, "PDF summary support is not available because the PDF reader package is missing."

    try:
        reader = PdfReader(str(path))
    except Exception:
        return None, f"I found {path.name}, but I could not open the PDF."

    extracted_pages = []
    for page in reader.pages[:3]:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text.strip():
            extracted_pages.append(page_text.strip())

    content = " ".join(extracted_pages).strip()
    if not content:
        return None, f"I found {path.name}, but I could not extract readable text from the PDF."

    return " ".join(content.split()), None


def _read_supported_file_text(path):
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _read_pdf_preview(path)

    if suffix in {".txt", ".md", ".py", ".json"}:
        try:
            return path.read_text(encoding="utf-8", errors="ignore").strip(), None
        except Exception:
            return None, f"I found {path.name}, but I could not read it."

    return (
        None,
        f"I found {path.name}, but question and answer is supported only for text-based files and PDFs right now.",
    )


def _split_text_chunks(content):
    parts = re.split(r"(?<=[.!?])\s+|\n+", content)
    chunks = []
    for part in parts:
        cleaned = " ".join(part.split()).strip()
        if cleaned:
            chunks.append(cleaned)
    return chunks


def _question_keywords(question):
    words = re.findall(r"[a-zA-Z0-9]+", question.lower())
    ignore = {
        "what",
        "is",
        "the",
        "in",
        "on",
        "of",
        "a",
        "an",
        "does",
        "do",
        "this",
        "that",
        "file",
        "pdf",
        "document",
        "say",
        "about",
        "tell",
        "me",
        "where",
        "who",
        "when",
        "why",
        "how",
    }
    return [word for word in words if word not in ignore and len(word) > 1]


def _best_matching_chunks(content, question, limit=3):
    chunks = _split_text_chunks(content)
    keywords = _question_keywords(question)

    if not chunks:
        return []

    if not keywords:
        return chunks[:limit]

    scored = []
    for chunk in chunks:
        lowered = chunk.lower()
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return [chunk for _, chunk in scored[:limit]]


def summarize_found_file(command):
    query = command
    prefixes = [
        "summarize file",
        "read file summary",
        "what is in file",
    ]

    for prefix in prefixes:
        if command.startswith(prefix):
            query = command.replace(prefix, "", 1)
            break

    query = query.strip(" :")
    if not query:
        return "Tell me which file you want me to summarize."

    matches = _find_files(query, limit=1)
    if not matches:
        return f"I could not find a file matching {query}."

    path = matches[0]
    content, error = _read_supported_file_text(path)
    if error:
        return error

    if not content:
        return f"{path.name} is empty."

    preview = " ".join(content.split())
    return f"Summary of {path.name}: {preview[:300]}"


def ask_found_file(command):
    patterns = [
        r"^ask file\s+(.+?)\s+(.+)$",
        r"^ask pdf\s+(.+?)\s+(.+)$",
        r"^ask document\s+(.+?)\s+(.+)$",
        r"^what does file\s+(.+?)\s+say about\s+(.+)$",
        r"^search document\s+(.+?)\s+for\s+(.+)$",
    ]

    file_query = None
    question = None
    matched_pattern = None

    for pattern in patterns:
        match = re.match(pattern, command)
        if match:
            file_query = match.group(1).strip(" :")
            question = match.group(2).strip(" :")
            matched_pattern = pattern
            break

    if not file_query or not question:
        return (
            "Use this format: ask file resume what is my experience, "
            "ask pdf invoice what is the total amount, or search document resume for networking."
        )

    matches = _find_files(file_query, limit=1)
    if not matches:
        return f"I could not find a file matching {file_query}."

    path = matches[0]
    content, error = _read_supported_file_text(path)
    if error:
        return error

    if not content:
        return f"{path.name} is empty."

    matching_chunks = _best_matching_chunks(content, question)
    if not matching_chunks:
        if matched_pattern and "search document" in matched_pattern:
            return f"I could not find anything relevant to {question} in {path.name}."
        return (
            f"I read {path.name}, but I could not find a clear answer for {question}. "
            f"Try a more specific keyword."
        )

    answer_preview = " | ".join(matching_chunks)
    return f"From {path.name}: {answer_preview[:700]}"
