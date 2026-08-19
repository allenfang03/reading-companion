import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import unicodedata
import re
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')


def extract_epub_title(book: epub.EpubBook) -> str:
    """Extract title from EPUB metadata, falling back to 'Unknown'."""
    title = book.get_metadata('DC', 'title')
    if title and title[0]:
        return title[0][0]
    
    # Try alternative metadata
    for identifier in book.get_metadata('DC', 'identifier'):
        pass  # Could use as fallback
    
    return "Unknown Title"


def strip_html_and_normalize(text: str) -> str:
    """Strip HTML tags and normalize Unicode (decompose ligatures)."""
    # Remove HTML tags
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text(separator=' ')
    
    # Normalize Unicode: decompose ligatures like fi, fl, ff
    text = unicodedata.normalize('NFKD', text)
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def parse_epub(file_path: str) -> Tuple[str, List[dict]]:
    """
    Parse an EPUB file and return (title, list of chapters).
    
    Returns:
        title: The book's title
        chapters: List of dicts with 'text', 'char_count' keys
    """
    book = epub.read_epub(file_path)
    title = extract_epub_title(book)
    
    chapters = []
    seen_content = set()  # Avoid duplicates
    
    # Get all HTML/XHTML items from the book
    items = list(book.get_items())
    
    # Try spine first (most reliable for reading order)
    try:
        spine = book.get_spine()
        for idx, spine_item in enumerate(spine):
            href = spine_item.get('href')
            if href and href not in seen_content:
                item = book.get_item_with_href(href)
                if item:
                    content = item.get_content()
                    if content:
                        text = strip_html_and_normalize(content.decode('utf-8', errors='ignore'))
                        if text and len(text) > 50:
                            chapters.append({
                                'text': text,
                                'char_count': len(text)
                            })
                            seen_content.add(href)
    except Exception:
        pass
    
    # If no chapters from spine, try all HTML items
    if not chapters:
        for item in items:
            href = item.get_name()
            if href and href not in seen_content:
                media_type = item.media_type
                # Look for XHTML/HTML content
                if 'html' in media_type.lower() or 'xml' in media_type.lower():
                    try:
                        content = item.get_content()
                        if content:
                            text = strip_html_and_normalize(content.decode('utf-8', errors='ignore'))
                            if text and len(text) > 50:
                                chapters.append({
                                    'text': text,
                                    'char_count': len(text)
                                })
                                seen_content.add(href)
                    except Exception:
                        continue
    
    if not chapters:
        raise ValueError("No readable chapters found in EPUB. The file may be DRM-protected or use an unsupported format.")
    
    return title, chapters


def validate_epub_file(file_path: str) -> bool:
    """Check if a file appears to be a valid EPUB."""
    try:
        # Read first bytes to check for ZIP signature
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'PK\x03\x04':  # ZIP magic number
                return False
        
        # Try to open as EPUB
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            book = epub.read_epub(file_path)
            # Basic check - does it have items?
            items = list(book.get_items())
            return len(items) > 0
    except Exception as e:
        print(f"EPUB validation error: {e}")
        return False


def get_epub_mimetype(file_path: str) -> str:
    """Get the mimetype from EPUB container.xml."""
    import zipfile
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            if 'mimetype' in z.namelist():
                mimetype = z.read('mimetype').decode('utf-8').strip()
                return mimetype
    except Exception:
        pass
    return ''
