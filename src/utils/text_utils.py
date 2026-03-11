"""Text normalization and utility functions."""

import re
from typing import List, Set


def normalize_text(text: str) -> str:
    """
    Normalize text by removing extra whitespace and cleaning common artifacts.
    
    Args:
        text: Raw text to normalize
        
    Returns:
        Normalized text
    """
    lines = text.split('\n')
    normalized_lines = []
    
    for line in lines:
        # Check if line looks like a table row (has wide gaps of 2+ spaces)
        # We replace wide gaps with " | " to preserve column structure for LLM
        if re.search(r' {2,}', line.strip()):
            # Replace 2 or more spaces with " | "
            # But avoid replacing indentation at start (handled by strip later)
            normalized_line = re.sub(r' {2,}', ' | ', line.strip())
            normalized_lines.append(normalized_line)
        else:
            # Standard normalization for non-table lines
            # Collapse multiple spaces
            line = re.sub(r' +', ' ', line)
            normalized_lines.append(line)
            
    text = '\n'.join(normalized_lines)
    
    # Collapse multiple newlines (keep paragraph breaks as double newline)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Fix common hyphenation at line breaks (only if hyphen is preceded by a letter)
    text = re.sub(r'([a-zA-Z])-\n([a-zA-Z])', r'\1\2', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def normalize_query(query: str) -> str:
    """
    Normalize user query while preserving important elements like numbers.
    
    Args:
        query: User's question
        
    Returns:
        Normalized query
    """
    # Trim whitespace
    query = query.strip()
    
    # Remove multiple spaces
    query = re.sub(r' +', ' ', query)
    
    return query


def extract_key_terms(query: str) -> str:
    """
    Extract key terms from query, especially course codes and important nouns.
    This helps with BM25 keyword matching by focusing on meaningful terms.
    
    Args:
        query: User's question
        
    Returns:
        Query with key terms emphasized and stop words removed
    """
    # Trim whitespace
    query = query.strip()
    
    # Remove multiple spaces
    query = re.sub(r' +', ' ', query)
    
    # Common stop words to remove (but keep if they're part of course codes)
    stop_words = {
        'what', 'is', 'are', 'was', 'were', 'the', 'a', 'an', 'and', 'or', 'but',
        'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'about',
        'can', 'could', 'should', 'would', 'will', 'do', 'does', 'did', 'have', 'has', 'had',
        'this', 'that', 'these', 'those', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how'
    }
    
    # Extract course codes (pattern: 2-4 letters followed by 3-4 digits, case insensitive)
    # Handles both formats: "EC200" and "EC 200" (with space)
    # Examples: EC100, ec200, CS101, MA201, EC 200, etc.
    course_code_pattern = r'\b([A-Za-z]{2,4})\s*(\d{3,4})\b'
    course_code_matches = re.findall(course_code_pattern, query, re.IGNORECASE)
    
    # Normalize course codes (remove spaces, uppercase) and track component parts
    course_codes = []
    processed_words = set()  # Track which words we've already processed as part of course codes
    
    for letters, digits in course_code_matches:
        code = f"{letters.upper()}{digits}"
        course_codes.append(code)
        # Mark the component parts as processed (so we don't add them separately)
        processed_words.add(letters.lower())
        processed_words.add(digits)
    
    # Tokenize query
    words = query.lower().split()
    
    # Collect important terms
    key_terms = []
    
    # First, add course codes (normalized to uppercase for consistency)
    for code in course_codes:
        key_terms.append(code)
    
    # Then add non-stop-word terms that aren't course codes
    for word in words:
        # Remove punctuation
        word_clean = re.sub(r'[^\w]', '', word)
        if not word_clean:
            continue
        
        # Skip if already processed as part of course code
        if word_clean in processed_words:
            continue
        
        # Skip if it's a stop word
        if word_clean in stop_words:
            continue
        
        # Skip if it's already a course code (we added it above)
        if re.match(r'^[a-z]{2,4}\d{3,4}$', word_clean, re.IGNORECASE):
            continue
        
        # Add meaningful terms (length > 2 or numbers)
        if len(word_clean) > 2 or word_clean.isdigit():
            key_terms.append(word_clean)
    
    # If we extracted key terms, return them; otherwise return original query
    if key_terms:
        # Join with spaces, ensuring course codes are prominent
        return ' '.join(key_terms)
    else:
        # Fallback to original query if no key terms found
        return query


def detect_section_heading(line: str) -> bool:
    """
    Detect if a line is likely a section heading.
    
    Args:
        line: Text line to check
        
    Returns:
        True if line appears to be a section heading
    """
    line = line.strip()
    
    # Empty line cannot be a heading
    if not line:
        return False
    
    # Check for numbered sections (e.g., "4.2.3 Title" or "1. Introduction")
    if re.match(r'^\d+\.(\d+\.)*\s+[A-Z]', line):
        return True
    
    # Check for all-caps headings (short lines)
    if len(line) < 100 and line.isupper() and len(line.split()) >= 2:
        return True
    
    # Check for title case headings
    if len(line) < 100 and line[0].isupper() and not line.endswith(('.', ',', ';')):
        words = line.split()
        if len(words) >= 2 and sum(1 for w in words if w[0].isupper()) >= len(words) * 0.5:
            return True
    
    return False


def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs based on double newlines.
    
    Args:
        text: Input text
        
    Returns:
        List of paragraphs
    """
    # Split by double newlines
    paragraphs = re.split(r'\n\s*\n', text)
    
    # Filter out empty paragraphs
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    return paragraphs


def extract_page_numbers_from_text(text: str) -> List[int]:
    """
    Extract page numbers that might be mentioned in text.
    
    Args:
        text: Text that may contain page references
        
    Returns:
        List of page numbers found
    """
    # Look for patterns like "page 42", "p. 42", "pg. 42"
    pattern = r'(?:page|p\.|pg\.)\s*(\d+)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return [int(m) for m in matches]


def clean_institutional_headers(text: str) -> str:
    """
    Remove repetitive institutional headers and footers from text.
    
    Args:
        text: Raw text that may contain institutional headers
        
    Returns:
        Cleaned text with headers removed
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    # Common institutional header and footer patterns
    header_patterns = [
        # Headers - Institution name variations
        r'NATIONAL INSTITUTE OF TECHNOLOGY KARNATAKA.*SURATHKAL',
        r'NATIONAL INSTITUTE OF TECHNOLOGY.*KARNATAKA',
        r'SRINIVASNAGAR.*MANGALORE',
        r'KARNATAKA.*INDIA',
        r'Phone:.*\+91-824',
        r'Web-Site:.*www\.nitk\.ac\.in',
        r'Fax.*\+91-824',
        r'^\s*[-=*]+\s*$',  # Lines with only dashes, equals, or asterisks
        r'^\s*$',  # Empty lines
        # r'^\s*\d+\s*$',  # REMOVED: Caused data loss for table values (e.g. credits "3", marks "100")
        r'CURRICULUM.*\d{4}',
        r'UNDERGRADUATE PROGRAMME',
        r'UNDERGRADUATE PROGRAMMES',
        r'B\.Tech\.',
        r'M\.Tech\.',
        r'Ph\.D\.',
        r'^\s*MOTTO\s*$',
        r'^\s*VISION\s*$',
        r'^\s*MISSION\s*$',
        r'^\s*Work is Worship\s*$',
        # Footers
        r'Page\s+\d+\s+of\s+\d+',  # "Page 5 of 10"
        r'NITK.*UG.*Curriculum.*\d{4}',  # "NITK- UG- Curriculum 2023"
        r'NITK.*PG.*Curriculum.*\d{4}',  # "NITK- PG- Curriculum 2023"
        r'NITK/\d{4}/(UG|PG)/Course Contents', # "NITK/2023/UG/Course Contents"
        r'NITK.*Regulations.*\d{4}',  # "NITK-Regulations (M.Tech.) 2023"
        r'NITK.*PGR.*\d{3}.*Level.*Courses.*\d{4}',  # "NITK – PGR - 900 Level Courses 2023"
        r'^\s*Page\s+\d+\s*$',  # Standalone "Page 5"
        r'^\s*\d+\s*/\s*\d+\s*$',  # "5 / 10" page numbers
    ]
    
    # Compile patterns for efficiency
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in header_patterns]
    
    prev_was_course_code = False

    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines
        if not line_stripped:
            prev_was_course_code = False
            continue

        is_course_code_line = bool(
            re.search(r'\b[A-Za-z]{2,4}\s*\d{3,4}\b', line_stripped)
        )
            
        # Check if line matches any header pattern
        is_header = False
        for pattern in compiled_patterns:
            if pattern.match(line_stripped):
                is_header = True
                break
        
        # Also check for lines that are mostly separators or very short
        if not is_header:
            # Skip lines that are mostly separators (very short lines with only separators)
            if len(line_stripped) <= 3 and all(c in '-=*' for c in line_stripped):
                is_header = True
            # Heuristic removed to preserve section headers (e.g. "SYLLABUS", "COURSE OBJECTIVES")
            # elif len(line_stripped) <= 30 and line_stripped.isupper() and len(line_stripped.split()) <= 3:
            #     if not is_course_code_line and not prev_was_course_code:
            #         is_header = True
        
        if not is_header:
            cleaned_lines.append(line)

        prev_was_course_code = is_course_code_line
    
    return '\n'.join(cleaned_lines)


def remove_repetitive_content(text: str, min_occurrences: int = 5) -> str:
    """
    Remove content that appears too frequently across the text.
    
    Args:
        text: Input text
        min_occurrences: Minimum number of occurrences to consider content repetitive
        
    Returns:
        Text with repetitive content removed
    """
    lines = text.split('\n')
    line_counts = {}
    
    # Count occurrences of each line
    for line in lines:
        line_stripped = line.strip()
        if line_stripped:
            line_counts[line_stripped] = line_counts.get(line_stripped, 0) + 1
    
    # Filter out repetitive lines
    filtered_lines = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_counts.get(line_stripped, 0) < min_occurrences:
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)


def clean_document_text(text: str) -> str:
    """
    Comprehensive text cleaning for document processing.
    
    Args:
        text: Raw document text
        
    Returns:
        Cleaned text ready for chunking
    """
    # First, remove institutional headers
    text = clean_institutional_headers(text)
    
    # Remove repetitive content - DISABLED as it removes valid repeated table data (e.g. "(3-0-0) 3")
    # text = remove_repetitive_content(text, min_occurrences=5)
    
    # Normalize the text
    text = normalize_text(text)
    
    return text


