#!/usr/bin/env python3
"""
Extract chapters from book.txt into individual files in chapters/ directory.
"""

import os
import re
import sys
import logging
import time
from pathlib import Path

def sanitize_filename(title):
    """Sanitize chapter title for filename use."""
    # Remove special characters and replace spaces with underscores
    sanitized = re.sub(r'[^\w\s-]', '', title.strip())
    sanitized = re.sub(r'[\s-]+', '_', sanitized)
    return sanitized

def parse_toc(book_content):
    """Parse table of contents from book content with validation."""
    toc_lines = []
    for line_num, line in enumerate(book_content.split('\n'), 1):
        if '\t' in line and not line.startswith('#'):
            try:
                title, page_num = line.split('\t', 1)
                title = title.strip()
                if not title:
                    logging.warning(f"Empty title in TOC at line {line_num}")
                    continue
                if not page_num.strip().isdigit():
                    logging.warning(f"Invalid page number in TOC at line {line_num}: {page_num}")
                toc_lines.append(title)
            except ValueError as e:
                logging.warning(f"Malformed TOC entry at line {line_num}: {line} - {e}")
    return toc_lines

def extract_chapters(book_content, toc):
    """Extract chapter contents based on TOC."""
    chapters = {}
    current_chapter = None
    content_lines = []
    
    for line in book_content.split('\n'):
        if line.upper() in [t.upper() for t in toc]:
            if current_chapter:
                chapters[current_chapter] = '\n'.join(content_lines).strip()
                content_lines = []
            current_chapter = line.strip()
        elif current_chapter:
            content_lines.append(line)
    
    if current_chapter and content_lines:
        chapters[current_chapter] = '\n'.join(content_lines).strip()
    
    return chapters

def validate_utf8(content):
    """Validate content is UTF-8 decodable."""
    try:
        # Attempt to encode the string to UTF-8. If it fails, it contains
        # characters not representable in UTF-8 (e.g., lone surrogates).
        content.encode('utf-8')
        return True
    except UnicodeEncodeError:
        return False

class ExtractionMetrics:
    """Track metrics during chapter extraction."""
    def __init__(self):
        self.chapter_sizes = {}
        self.error_count = 0
        self.duplicates_found = 0
        self.invalid_utf8 = 0
        self.successful_writes = 0

def write_chapter_files(chapters, output_dir='chapters', metrics=None):
    """Write chapter contents to individual files with retry logic and metrics."""
    Path(output_dir).mkdir(exist_ok=True)
    
    if metrics is None:
        metrics = ExtractionMetrics()
    
    seen_content = set()
    
    for i, (title, content) in enumerate(chapters.items(), 1):
        if not validate_utf8(content):
            print(f"Warning: Chapter {i} contains invalid UTF-8 characters")
            metrics.invalid_utf8 += 1
            continue
            
        # Check for duplicate content
        content_hash = hash(content)
        if content_hash in seen_content:
            metrics.duplicates_found += 1
            logging.warning(f"Duplicate content detected in chapter {i}")
        seen_content.add(content_hash)
        
        sanitized_title = sanitize_filename(title)
        filename = f"{i:02d}_{sanitized_title}.txt"
        filepath = os.path.join(output_dir, filename)
        metrics.chapter_sizes[filename] = len(content.encode('utf-8'))
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Created: {filepath}")
                metrics.successful_writes += 1
                break
            except IOError as e:
                if attempt == max_attempts:
                    logging.error(f"Failed to write {filepath} after {max_attempts} attempts: {e}")
                    metrics.error_count += 1
                else:
                    logging.warning(f"Attempt {attempt} failed for {filepath}, retrying...")
                    time.sleep(1 * attempt)  # Exponential backoff

def load_checkpoint():
    """Load progress checkpoint if exists."""
    checkpoint_file = '.chapter_extract_checkpoint'
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                return int(f.read().strip())
        except (IOError, ValueError):
            logging.warning("Invalid checkpoint file, starting from beginning")
    return 0

def save_checkpoint(index):
    """Save progress checkpoint."""
    with open('.chapter_extract_checkpoint', 'w') as f:
        f.write(str(index))

def cleanup_checkpoint():
    """Remove checkpoint file if exists."""
    if os.path.exists('.chapter_extract_checkpoint'):
        try:
            os.remove('.chapter_extract_checkpoint')
        except IOError as e:
            logging.warning(f"Failed to remove checkpoint file: {e}")

def generate_validation_report(metrics, output_file='docs/validation_report.md'):
    """Generate markdown validation report from metrics."""
    report = f"""## Chapter Extraction Validation Report
    
### Metrics
- Total chapters processed: {len(metrics.chapter_sizes)}
- Successful writes: {metrics.successful_writes}
- Errors encountered: {metrics.error_count}
- Invalid UTF-8 chapters: {metrics.invalid_utf8}
- Duplicate content found: {metrics.duplicates_found}
- Total storage used: {sum(metrics.chapter_sizes.values())} bytes

```mermaid
pie title Validation Summary
    "Success" : {metrics.successful_writes}
    "Errors" : {metrics.error_count}
    "Invalid UTF-8" : {metrics.invalid_utf8}
    "Duplicates" : {metrics.duplicates_found}
```
"""
    Path(output_file).parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

def main():
    """Main execution function with progress saving and metrics."""
    if not os.path.exists('book.txt'):
        print("Error: book.txt not found", file=sys.stderr)
        return 1
    
    metrics = ExtractionMetrics()
    
    try:
        with open('book.txt', 'r', encoding='utf-8') as f:
            book_content = f.read()
    except IOError as e:
        print(f"Error reading book.txt: {e}", file=sys.stderr)
        return 1
    
    toc = parse_toc(book_content)
    chapters = extract_chapters(book_content, toc)
    
    if not chapters:
        print("Error: No chapters found", file=sys.stderr)
        return 1
    
    # Load progress checkpoint
    start_index = load_checkpoint()
    if start_index > 0:
        print(f"Resuming from chapter {start_index}")
    
    # Filter chapters to process only unprocessed ones
    chapters_to_process = {
        k: v for i, (k, v) in enumerate(chapters.items(), 1)
        if i >= start_index
    }
    
    try:
        write_chapter_files(chapters_to_process, metrics=metrics)
        
        # Verification
        print(f"\nExtracted {len(chapters)} chapters:")
        for i, title in enumerate(chapters.keys(), 1):
            print(f"{i:02d}. {title}")
        
        # Generate validation report
        generate_validation_report(metrics)
        
        # Clean up checkpoint on success
        cleanup_checkpoint()
        return 0
    except Exception as e:
        logging.error(f"Processing interrupted: {e}")
        # Save checkpoint for resume
        processed_count = len(chapters) - len(chapters_to_process)
        if processed_count > 0:
            save_checkpoint(processed_count + 1)
        return 1

if __name__ == '__main__':
    sys.exit(main())