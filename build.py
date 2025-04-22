#!/usr/bin/env python3
"""
Frank Dunn Memoirs - Static Site Builder

This script handles the generation of static HTML files from content sources,
working alongside the existing Vite build system for assets.
"""

import argparse
import sys
import json
import logging
import os
import re
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError
from PIL import Image
import hashlib
import subprocess

# Constants
DIST_DIR = "dist"
REPORTS_DIR = "reports"
CHAPTERS_DIR = "chapters"
ASSETS_DIR = "assets"

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Build static site for Frank Dunn Memoirs")
    parser.add_argument("--output", "-o",
                       default=DIST_DIR,
                       help="Output directory for built site")
    parser.add_argument("--clean",
                       action="store_true",
                       help="Clean output directory before building")
    return parser.parse_args()

def parse_chapter_summary(markdown_text: str) -> dict:
    """
    Parse chapter summary from markdown report
    Returns a dictionary with:
    - chapter_number
    - title
    - summary
    - keywords
    - primary_image
    """
    chapter = {}
    
    # Extract chapter number and title
    chapter_match = re.search(r'### Chapter (\d+): ([^\.]+)\.txt', markdown_text)
    if chapter_match:
        chapter['number'] = int(chapter_match.group(1))
        chapter['title'] = chapter_match.group(2).strip()
    
    # Extract summary
    summary_match = re.search(r'\*\*Summary\*\*:([^\*]+)', markdown_text, re.DOTALL)
    if summary_match:
        chapter['summary'] = summary_match.group(1).strip()
    
    # Extract keywords
    keywords_match = re.search(r'\*\*Keywords\*\*: ([^\n]+)', markdown_text)
    if keywords_match:
        chapter['keywords'] = [kw.strip() for kw in keywords_match.group(1).split(',')]
    
    # Extract primary image
    image_match = re.search(r'!\[Chapter Illustration\]\(([^\)]+)\)', markdown_text)
    if image_match:
        chapter['primary_image'] = image_match.group(1).strip()
    
    return chapter

def parse_summary_report(report_path):
    """
    Parse the full chapter summary report
    Returns a list of chapter dictionaries
    """
    with open(report_path, 'r') as f:
        content = f.read()
    
    # Split into individual chapter sections
    chapters = []
    for section in content.split('---'):
        if '### Chapter' in section:
            chapters.append(parse_chapter_summary(section))
    
    return chapters

def ensure_directory(path):
    """Ensure directory exists, create if needed"""
    Path(path).mkdir(parents=True, exist_ok=True)

def optimize_images(src_dir="assets/images", output_dir="dist/assets/images"):
    """
    Process and optimize images from src_dir to output_dir
    Creates production-ready WebP versions while preserving aspect ratio
    
    Args:
        src_dir: Source directory containing original images
        output_dir: Destination directory for optimized images
    Returns:
        Number of successfully processed images
    """
    from PIL import Image
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    processed = 0
    for img_path in Path(src_dir).rglob('*'):
        if img_path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            try:
                with Image.open(img_path) as img:
                    # Preserve aspect ratio
                    img.thumbnail((1200, 1200))
                    webp_path = output_path / f"{img_path.stem}.webp"
                    img.save(webp_path, "WEBP", quality=85, method=6)
                    processed += 1
            except Exception as e:
                logging.warning(f"Error processing {img_path.name}: {str(e)}")
                continue
    return processed

def asset_hash(path):
    """
    Generate cache-busting hash for static assets
    
    Args:
        path: Path to asset file
    Returns:
        String containing first 8 chars of MD5 hash
    """
    return hashlib.md5(Path(path).read_bytes()).hexdigest()[:8]

def generate_search_index(chapters: list[dict]) -> list[dict]:
    """
    Generate a search index JSON file from parsed chapter data
    Optimized for Fuse.js fuzzy searching with threshold=0.3
    
    Args:
        chapters: List of chapter dictionaries with all parsed data
    
    Returns:
        List of searchable chapter objects with all available metadata
    """
    search_index = []
    
    for chapter in chapters:
        # Get first 150 characters of summary
        summary = chapter.get('summary', '')
        if len(summary) > 150:
            summary = summary[:150] + '...'
            
        entry = {
            "chapter_number": chapter['number'],
            "title": f"Chapter {chapter['number']}: {chapter['title']}",
            "summary": summary,
            "keywords": chapter.get('keywords', []),
            "date_ranges": chapter.get('date_ranges', []),
            "locations": chapter.get('extracted_location_tags', []),
            "word_count": chapter.get('word_count', 0),
            "slug": chapter['title'].lower().replace(' ', '_'),
            "image_path": chapter.get('primary_image', ''),
            # Fuse.js compatibility fields
            "id": f"chapter-{chapter['number']}",
            "metadata": {
                "title": chapter['title'],
                "number": chapter['number']
            }
        }
        search_index.append(entry)
    
    return search_index

def write_search_index(chapters, output_dir):
    """
    Write search index JSON file to output directory with environment-aware formatting
    
    Args:
        chapters: List of chapter dictionaries from parse_summary_report()
        output_dir: Directory to write search-index.json to
    """
    search_index = generate_search_index(chapters)
    
    # Validate before writing
    validate_search_index(search_index)
    
    output_path = os.path.join(output_dir, "assets", "data")
    os.makedirs(output_path, exist_ok=True)
    
    # Environment-aware formatting
    is_production = os.getenv('NODE_ENV') == 'production'
    
    with open(os.path.join(output_path, "search-index.json"), 'w') as f:
        if is_production:
            json.dump(search_index, f, separators=(',', ':'))  # Minified
        else:
            json.dump(search_index, f, indent=2)  # Pretty-printed
    
    # Check compressed size
    check_index_size(os.path.join(output_path, "search-index.json"))

def validate_search_index(search_index: list[dict]):
    """Validate search index meets requirements"""
    required_fields = ['title', 'summary', 'chapter_number', 'slug']
    
    for entry in search_index:
        # Check required fields
        for field in required_fields:
            if not entry.get(field):
                raise ValueError(f"Search index entry missing required field: {field}")
        
        # Validate image paths
        if entry['image_path'] and not os.path.exists(os.path.join(ASSETS_DIR, entry['image_path'])):
            raise FileNotFoundError(f"Image path does not exist: {entry['image_path']}")
        
        # Check for empty search fields
        if not entry['summary'] or not entry['title']:
            logging.warning(f"Chapter {entry['chapter_number']} has empty searchable fields")

def check_index_size(file_path: str):
    """Check if search index exceeds size limit"""
    size_kb = os.path.getsize(file_path) / 1024
    if size_kb > 100:
        logging.warning(f"Search index size ({size_kb:.1f}KB) exceeds recommended 100KB limit")

def generate_html_files(chapters: list[dict], output_dir: str, site_config: dict):
    """
    Generate HTML files for each chapter and index page using Jinja2 templates
    
    Args:
        chapters: List of chapter dictionaries with all parsed data
        output_dir: Base output directory for the built site
        site_config: Site configuration dictionary
    
    Raises:
        TemplateNotFound: If template file is missing
        TemplateSyntaxError: If template contains syntax errors
        IOError: If unable to write output files
    """
    try:
        env = Environment(loader=FileSystemLoader("templates"))
        
        # Process chapters to add slugs
        processed_chapters = []
        for chapter in chapters:
            # Generate consistent slug format
            slug = chapter["title"].lower()
            slug = re.sub(r'^\d+_', '', slug)  # Remove number prefix
            slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
            slug = re.sub(r'[\s]+', '-', slug)  # Replace spaces with hyphens
            slug = slug.strip('-')  # Trim hyphens from ends
            
            processed_chapters.append({
                **chapter,
                "slug": slug,
                "number": chapter["number"]
            })
        
        # Get templates
        chapter_template = env.get_template("chapter_detail.html")
        index_template = env.get_template("index.html")
        base_template = env.get_template("base.html")
        
        # Create chapters output directory
        chapters_dir = os.path.join(output_dir, "chapters")
        os.makedirs(chapters_dir, exist_ok=True)
        
        for chapter in chapters:
            try:
                # Prepare template context
                chapter_data = next((c for c in processed_chapters if c["number"] == chapter["number"]), None)
                if not chapter_data:
                    continue
                    
                context = {
                    "chapter": {
                        "title": chapter_data["title"],
                        "slug": chapter_data["slug"],
                        "raw_text": chapter.get("raw_text", ""),
                        "featured_image": chapter.get("primary_image", ""),
                        "images": []  # Can be populated later if needed
                    },
                    "chapters": processed_chapters,
                    "site_config": site_config,
                    "audio_file_url": "",  # Can be populated later if needed
                    "related_chapters": []  # Can be populated later if needed
                }
                
                # Render template
                output = chapter_template.render(context)
                
                # Write to file
                output_path = os.path.join(chapters_dir, f"{chapter_data['slug']}.html")
                with open(output_path, "w") as f:
                    f.write(output)
                    
                logging.debug(f"Generated HTML for chapter: {chapter['title']}")
                
                # Validate chapter file was created
                chapter_path = Path(output_path)
                if not chapter_path.exists():
                    print(f"❌ Chapter file missing - check template rendering: {chapter_path}")
                else:
                    print(f"✅ Chapter file exists: {chapter_path}")
                
            except Exception as e:
                logging.error(f"Failed to generate HTML for chapter {chapter['title']}: {str(e)}")
                raise
                
        # Generate index.html
        index_context = {
            "chapters": processed_chapters,
            "site_config": site_config
        }
        index_output = index_template.render(index_context)
        index_path = os.path.join(output_dir, "index.html")
        with open(index_path, "w") as f:
            f.write(index_output)
            
        logging.debug("Generated index.html")
        
    except TemplateNotFound as e:
        logging.error(f"Template not found: {str(e)}")
        raise
    except TemplateSyntaxError as e:
        logging.error(f"Template syntax error: {str(e)}")
        raise
    except IOError as e:
        logging.error(f"File system error during HTML generation: {str(e)}")
        raise

def validate_html_files(output_dir: str, expected_count: int = 47):
    """
    Validate generated HTML files meet requirements
    
    Args:
        output_dir: Base output directory for the built site
        expected_count: Expected number of chapter HTML files
    
    Raises:
        ValueError: If validation fails
    """
    chapters_dir = os.path.join(output_dir, "chapters")
    
    # Check directory exists
    if not os.path.exists(chapters_dir):
        raise ValueError(f"Chapters directory not found: {chapters_dir}")
    
    # Count HTML files
    html_files = [f for f in os.listdir(chapters_dir) if f.endswith(".html")]
    if len(html_files) < expected_count:
        raise ValueError(f"Expected {expected_count} chapter HTML files, found {len(html_files)}")
    
    # Check file sizes
    for html_file in html_files:
        file_path = os.path.join(chapters_dir, html_file)
        if os.path.getsize(file_path) < 100:  # Minimum reasonable size
            raise ValueError(f"HTML file too small: {html_file}")

def clean_directory(path):
    """Clean output directory if it exists"""
    if os.path.exists(path):
        shutil.rmtree(path)
    ensure_directory(path)

def validate_input_files():
    """Validate required input files and consistency"""
    # Check directories exist
    required_dirs = [REPORTS_DIR, CHAPTERS_DIR, ASSETS_DIR]
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            raise FileNotFoundError(f"Required directory not found: {dir_path}")
    
    # Check required reports exist
    required_reports = [
        "chapter_summary_report.md",
        "chapter_dates_report.md"
    ]
    for report in required_reports:
        report_path = os.path.join(REPORTS_DIR, report)
        if not os.path.exists(report_path):
            raise FileNotFoundError(f"Required report not found: {report_path}")
    
    # Check chapter files exist
    chapter_files = [f for f in os.listdir(CHAPTERS_DIR) if f.endswith('.txt')]
    if not chapter_files:
        raise FileNotFoundError(f"No chapter text files found in {CHAPTERS_DIR}")
    
    # Check images exist for chapters
    summary_report = parse_summary_report(os.path.join(REPORTS_DIR, "chapter_summary_report.md"))
    for chapter in summary_report:
        if 'primary_image' in chapter:
            image_path = os.path.join(ASSETS_DIR, chapter['primary_image'])
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Chapter image not found: {image_path}")

def setup_logging():
    """Configure basic logging for the build process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def parse_chapter_dates(markdown_text: str) -> dict:
    """
    Parse chapter dates from markdown report
    Returns a dictionary with:
    - number: chapter number (defaults to 0 if not found)
    - date_ranges: list of date ranges
    - significant_dates: list of significant dates
    """
    chapter = {'number': 0, 'date_ranges': [], 'significant_dates': []}
    
    try:
        # Extract chapter number from table row
        chapter_match = re.search(r'^\| (\d+) \|', markdown_text)
        if chapter_match:
            chapter['number'] = int(chapter_match.group(1))
        
        # Extract date ranges and significant dates
        dates_match = re.search(r'LLM Year[^\|]+\| ([^\|]+) \|', markdown_text)
        if dates_match:
            date_str = dates_match.group(1).strip()
            if '-' in date_str:
                chapter['date_ranges'] = date_str.split('-')
            else:
                chapter['date_ranges'] = [date_str]
        
        reasoning_match = re.search(r'Reasoning \|\n\|[^\|]+\|([^\|]+)\|', markdown_text, re.DOTALL)
        if reasoning_match:
            chapter['significant_dates'] = [
                line.strip() for line in reasoning_match.group(1).split('\n')
                if line.strip()
            ]
    except Exception as e:
        logging.warning(f"Failed to parse chapter dates: {str(e)}")
    
    return chapter

def parse_chapter_text(file_path: str) -> dict:
    """
    Parse chapter text file
    Returns a dictionary with:
    - raw_text
    - word_count
    - extracted_location_tags
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Count words (simple whitespace split)
    word_count = len(content.split())
    
    # Extract location tags (simple pattern matching)
    location_tags = set()
    location_patterns = [
        r'in ([A-Z][a-z]+(?: [A-Z][a-z]+)*)',
        r'at ([A-Z][a-z]+(?: [A-Z][a-z]+)*)',
        r'near ([A-Z][a-z]+(?: [A-Z][a-z]+)*)'
    ]
    
    for pattern in location_patterns:
        for match in re.finditer(pattern, content):
            location_tags.add(match.group(1))
    
    return {
        'raw_text': content,
        'word_count': word_count,
        'extracted_location_tags': list(location_tags)
    }

def main():
    setup_logging()
    args = parse_args()
    
    # Verify Pillow installation
    try:
        from PIL import Image
        print("✓ Pillow available")
        
        # Verify WebP support
        ensure_directory("dist")
        test_img = Image.new('RGB', (100, 100))
        test_img.save(Path("dist/test.webp"), "WEBP")
        Path("dist/test.webp").unlink()
    except Exception as e:
        print(f"Image processing test failed: {str(e)}")
        sys.exit(1)

    try:
        # Validate input files before proceeding
        validate_input_files()
        
        # Clean/setup output directory
        if args.clean:
            logging.info(f"Cleaning output directory: {args.output}")
            clean_directory(args.output)
        else:
            ensure_directory(args.output)
        
        logging.info(f"Building site to {args.output}")
        
        # Parse all reports
        chapters = parse_summary_report("reports/chapter_summary_report.md")
        
        # Parse dates report and merge with chapter data
        with open("reports/chapter_dates_report.md", 'r') as f:
            dates_content = f.read()
            dates_chapters = []
            for section in dates_content.split('---'):
                if '|' in section:  # Table row marker
                    dates_chapters.append(parse_chapter_dates(section))
            
            # Merge dates data with chapters
            for chapter in chapters:
                try:
                    matching_dates = next(
                        (d for d in dates_chapters if d.get('number', 0) == chapter['number']),
                        {'date_ranges': [], 'significant_dates': []}
                    )
                    chapter.update(matching_dates)
                except Exception as e:
                    logging.warning(f"Failed to merge dates for chapter {chapter['number']}: {str(e)}")
                    chapter.update({'date_ranges': [], 'significant_dates': []})
        
        # Parse each chapter text
        for chapter in chapters:
            try:
                chapter_file = f"{CHAPTERS_DIR}/{chapter['title']}.txt"
                chapter.update(parse_chapter_text(chapter_file))
            except Exception as e:
                logging.warning(f"Failed to parse chapter {chapter['number']}: {str(e)}")
                chapter.update({
                    'raw_text': '',
                    'word_count': 0,
                    'extracted_location_tags': []
                })
        
        # Generate search index with all data
        write_search_index(chapters, args.output)
        
        # Process and optimize images first
        processed_count = optimize_images()
        logging.info(f"Successfully processed {processed_count}/47 chapter images")
        
        # Run Vite build
        print("✅ Content built successfully. Run 'npm run build:assets' to build frontend assets")
        
        # Copy assets with conflict handling
        src_assets = Path('dist/assets')
        dest_assets = Path(args.output)/'assets'
        
        if src_assets.resolve() != dest_assets.resolve():
            if dest_assets.exists():
                shutil.rmtree(dest_assets)
            shutil.copytree(src_assets, dest_assets)
        
        # Generate HTML files with cache-busted assets
        site_config = {
            "title": "Frank Dunn: Memoirs of the North",
            "base_url": "/",
            "asset_hash": asset_hash  # Make hash function available in templates
        }
        generate_html_files(chapters, args.output, site_config)
        
        # Validate HTML output
        validate_html_files(args.output)
        
        logging.info("Build complete")
    except Exception as e:
        logging.error(f"Build failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()