
#!/usr/bin/env python3
"""
Enhanced chapter date analysis with LLM content evaluation.
"""

import os
import re
import sys
from pathlib import Path
from llm_analyzer import DeepseekAnalyzer

def extract_chapter_info(filename):
    """Extract chapter number, title and year from filename."""
    # Match pattern: NN_Title.txt with optional year anywhere
    match = re.match(r'^(\d+)_(.+?)\.txt$', filename)
    if not match:
        return None
    
    chapter_num = int(match.group(1))
    title_parts = match.group(2).split('_')
    title = ' '.join(title_parts)
    
    # Find all potential year matches in filename
    year_matches = re.findall(r'(?:^|_)((?:19|20)\d{2})(?:_|$)', filename)
    year_matches += re.findall(r'(?:^|_)(\d{2})(?:_|$)', filename)  # Also check 2-digit years
    
    # Process found years - take most recent 4-digit year, or convert 2-digit years
    years = []
    for y in year_matches:
        if len(y) == 4:
            years.append(y)
        elif len(y) == 2:  # Convert YY to YYYY
            years.append(f"19{y}" if int(y) > 30 else f"20{y}")
    
    year = max(years) if years else "unknown"
    
    return {
        'number': chapter_num,
        'title': title,
        'year': year
    }

def generate_report(chapters, output_file):
    """Generate enhanced markdown report with LLM analysis."""
    report = """# Chapter Dates Analysis Report

## Summary
- **Total Chapters**: {total}
- **Consistent Dates**: {consistent}
- **Filename Years Only**: {filename_only}
- **LLM Years Only**: {llm_only}
- **Conflicts**: {conflicts}
- **Low Confidence**: {low_confidence}

| Chapter | Title | Filename Year | LLM Year | Confidence | Validation Status | Reasoning |
|---------|-------|---------------|----------|------------|-------------------|-----------|
""".format(
        total=len(chapters),
        consistent=sum(1 for c in chapters if c.get('validation_status') == 'Consistent'),
        filename_only=sum(1 for c in chapters if c.get('validation_status') == 'Filename year only'),
        llm_only=sum(1 for c in chapters if c.get('validation_status') == 'LLM year only'),
        conflicts=sum(1 for c in chapters if 'Conflict' in c.get('validation_status', '')),
        low_confidence=sum(1 for c in chapters if 'Low confidence' in c.get('validation_status', ''))
    )
    
    for chapter in sorted(chapters, key=lambda x: x['number']):
        reasoning = chapter.get('reasoning', '')
        truncated_reasoning = (reasoning[:100] + '...') if len(reasoning) > 100 else reasoning
        report += (
            f"| {chapter['number']} | {chapter['title']} | "
            f"{chapter.get('year', 'unknown')} | "
            f"{chapter.get('llm_year', 'unknown')} | "
            f"{chapter.get('confidence', 0):.1f} | "
            f"{chapter.get('validation_status', '')} | "
            f"{truncated_reasoning} |\n"
        )
    
    Path(output_file).parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

def process_chapter(filepath):
    """Process a chapter file with both filename and content analysis."""
    filename = os.path.basename(filepath)
    info = extract_chapter_info(filename)
    
    if info is None:
        return {
            'filename': filename,
            'validation_status': 'Invalid filename format'
        }
    
    # Check file exists first
    if not os.path.exists(filepath):
        return {
            'filename': filename,
            'validation_status': f"Analysis error: File not found: {filepath}"
        }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        llm_analysis = DeepseekAnalyzer().analyze_chapter(content)
        info.update({
            'llm_year': llm_analysis['year'],
            'confidence': llm_analysis['confidence'],
            'reasoning': llm_analysis['reasoning'],
            'validation_status': validate_analysis(info, llm_analysis),
            'raw_response': llm_analysis.get('raw_response'),
            'full_response': llm_analysis.get('full_response'),
            'api_response': llm_analysis.get('api_response')
        })
    except Exception as e:
        info['validation_status'] = f"Analysis error: {str(e)}"
    
    return info

def validate_analysis(base_info, llm_data):
    """Validate LLM analysis against filename metadata with enhanced logic."""
    # Check for invalid LLM data first
    if not isinstance(llm_data.get('year'), str):
        return "Analysis error: Invalid LLM year"
    if not isinstance(llm_data.get('confidence'), (int, float)):
        return "Analysis error: Invalid confidence"
    
    # Handle cases where filename year is unknown
    if base_info['year'] == 'unknown':
        if llm_data['year'] == 'unknown':
            return "No year data"
        return "Consistent" if llm_data['confidence'] >= 0.5 else "Low confidence"
    
    # Handle cases where LLM year is unknown
    if llm_data['year'] == 'unknown':
        return "Filename year only"
    
    # Handle exact matches
    if base_info['year'] == llm_data['year']:
        return "Consistent"
    
    # Handle decade matches (e.g. 1967 vs 1965)
    base_decade = base_info['year'][:3] + '0'
    llm_decade = llm_data['year'][:3] + '0'
    if base_decade == llm_decade:
        return f"Same decade (filename={base_info['year']}, LLM={llm_data['year']})"
    
    # Handle low confidence cases
    if llm_data['confidence'] < 0.5:
        return "Low confidence"
    
    # All other cases are conflicts
    return f"Conflict: filename={base_info['year']} vs LLM={llm_data['year']}"

def main(chapters_dir='chapters', output_file='reports/chapter_dates_report.md'):
    """Enhanced main execution with LLM analysis.
    
    Args:
        chapters_dir: Path to directory containing chapter files
        output_file: Path for output report file
    
    Returns:
        0 on success, 1 on error
    """
    # Validate input directory exists
    if not os.path.exists(chapters_dir):
        print(f"Error: {chapters_dir} directory not found", file=sys.stderr)
        return 1
    
    # Process all chapter files
    chapters = []
    for filename in sorted(os.listdir(chapters_dir)):
        if filename.endswith('.txt'):
            filepath = os.path.join(chapters_dir, filename)
            try:
                chapter_info = process_chapter(filepath)
                chapters.append(chapter_info)
                print(f"Processed: {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {e}", file=sys.stderr)
                chapters.append({
                    'filename': filename,
                    'validation_status': f"Processing error: {str(e)}"
                })
    
    if not chapters:
        print("Error: No chapter files found", file=sys.stderr)
        return 1
    
    # Generate comprehensive report
    generate_report(chapters, output_file)
    print(f"\nReport generated at: {output_file}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
