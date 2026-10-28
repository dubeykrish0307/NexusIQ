import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import docx
import fitz  # PyMuPDF


@dataclass
class ParsedDocument:
    file_name: str
    file_type: str
    raw_text: str
    pages: list[str]
    page_count: int
    detected_title: Optional[str]
    detected_date: Optional[str]
    document_category: str
    char_count: int
    word_count: int


TITLE_PATTERNS = [
    r'(?i)^(ANNUAL REPORT|10-K|FORM 10-K|QUARTERLY REPORT|10-Q)\b',
    r'(?i)(ANNUAL REPORT\s+(?:FOR|FISCAL YEAR)\s+\d{4})',
    r'(?i)((?:FORM|SEC)\s+10-[KQ])',
]

DATE_PATTERNS = [
    r'(?i)(?:fiscal year|year ended?|for the year)\s+(\w+ \d{1,2},?\s+\d{4})',
    r'(?i)(?:fiscal year|year ended?|for the year)\s+(\d{4})',
    r'(\b(?:January|February|March|April|May|June|July|August|'
    r'September|October|November|December)\s+\d{1,2},\s+\d{4}\b)',
    r'\b(\d{4})\b',
]

# checked in order, first match wins
CATEGORY_KEYWORDS = [
    ("Annual Report (10-K)", ['annual report', '10-k', 'form 10-k', 'fiscal year', 'shareholders', 'stockholders']),
    ("Quarterly Report (10-Q)", ['10-q', 'quarterly report', 'quarter ended']),
    ("Legal Contract", ['agreement', 'contract', 'whereas', 'hereinafter', 'party of the first', 'terms and conditions']),
    ("Research Paper", ['abstract', 'introduction', 'methodology', 'conclusion', 'references', 'doi']),
    ("IPO Prospectus", ['prospectus', 'offering', 'underwriter', 's-1']),
]


def _group(items: list[str], size: int) -> list[str]:
    return ["\n\n".join(items[i:i + size]) for i in range(0, len(items), size)]


class DocumentParser:
    SUPPORTED_TYPES = {".pdf", ".docx", ".txt", ".md"}

    def parse(self, file_path: str) -> ParsedDocument:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if suffix not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported file type: {path.suffix}. Supported: {self.SUPPORTED_TYPES}")

        if suffix == ".pdf":
            pages, raw_text = self._parse_pdf(path)
        elif suffix == ".docx":
            pages, raw_text = self._parse_docx(path)
        else:
            pages, raw_text = self._parse_text(path)

        text = self._clean_text(raw_text)

        return ParsedDocument(
            file_name=path.name,
            file_type=suffix,
            raw_text=text,
            pages=pages,
            page_count=len(pages),
            detected_title=self._detect_title(text, path.name),
            detected_date=self._detect_date(text),
            document_category=self._detect_category(text, path.name),
            char_count=len(text),
            word_count=len(text.split()),
        )

    def _parse_pdf(self, path: Path) -> tuple[list[str], str]:
        with fitz.open(str(path)) as doc:
            pages = [page.get_text("text") for page in doc]
        return pages, "\n\n".join(pages)

    def _parse_docx(self, path: Path) -> tuple[list[str], str]:
        # .docx has no real pages, so every 20 paragraphs count as one
        paragraphs = [p.text.strip() for p in docx.Document(str(path)).paragraphs if p.text.strip()]
        return _group(paragraphs, 20), "\n\n".join(paragraphs)

    def _parse_text(self, path: Path) -> tuple[list[str], str]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()
        sections = [s.strip() for s in raw_text.split("\n\n") if s.strip()]
        return _group(sections, 10), raw_text

    def _clean_text(self, text: str) -> str:
        # strip control characters, collapse runs of spaces and blank lines,
        # and drop lines that are only a page number
        text = re.sub(r'\x00', '', text)
        text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'-{3,}', '---', text)
        return text.strip()

    def _detect_title(self, text: str, filename: str) -> Optional[str]:
        for pattern in TITLE_PATTERNS:
            match = re.search(pattern, text[:500])
            if match:
                return match.group(0).strip()

        first_line = text.split('\n')[0].strip()
        if 10 < len(first_line) < 100:
            return first_line

        return Path(filename).stem.replace('_', ' ').replace('-', ' ')

    def _detect_date(self, text: str) -> Optional[str]:
        for pattern in DATE_PATTERNS:
            match = re.search(pattern, text[:2000])
            if match:
                return match.group(1).strip()
        return None

    def _detect_category(self, text: str, filename: str) -> str:
        head = text[:3000].lower()
        for category, keywords in CATEGORY_KEYWORDS:
            if any(word in head for word in keywords):
                return category
        return "General Document"
