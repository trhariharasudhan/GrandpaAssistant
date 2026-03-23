import os
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
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        content, error = _read_pdf_preview(path)
        if error:
            return error
    elif suffix in {".txt", ".md", ".py", ".json"}:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            return f"I found {path.name}, but I could not read it."
    else:
        return f"I found {path.name}, but quick summary is supported only for text-based files and PDFs right now."

    if not content:
        return f"{path.name} is empty."

    preview = " ".join(content.split())
    return f"Summary of {path.name}: {preview[:300]}"
