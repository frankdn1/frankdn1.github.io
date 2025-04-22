#!/usr/bin/env python3
"""
Analyze book chapters to generate summaries and location data.
"""

import os
import logging
from pathlib import Path
from llm_analyzer import DeepseekAnalyzer

class ChapterAnalysis:
    def __init__(self):
        self.analyzer = DeepseekAnalyzer()
        self.metrics = {
            'chapters_processed': 0,
            'errors': 0,
            'missing_locations': 0
        }

    def analyze_chapter(self, chapter_file, chapter_dir):
        """Analyze a single chapter file."""
        chapter_path = os.path.join(chapter_dir, chapter_file)
        logging.info(f"Processing chapter: {chapter_file}")
        
        try:
            with open(chapter_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get chapter summary and location data
            logging.info(f"Analyzing date for {chapter_file}")
            date_result = self.analyzer.analyze_date(content)
            
            logging.info(f"Analyzing location for {chapter_file}")
            location_result = self.analyzer.analyze_location(content)
            summary_result = self.analyzer.analyze_summary(content)
            
            # Generate chapter image if summary is available
            # Extract chapter number from filename (e.g. "24_Murder..." -> 24)
            chapter_num = int(chapter_file.split('_')[0])
            image_path = None
            if 'summary' in summary_result:
                image_path = self.analyzer.generate_chapter_image(
                    summary_result['summary'],
                    chapter_num
                )
            
            self.metrics['chapters_processed'] += 1
            logging.info(f"Completed analysis for {chapter_file}")
            
            if location_result.get('location', {}).get('name') == 'unknown':
                self.metrics['missing_locations'] += 1
            
            return {
                'date': date_result,
                'location': location_result,
                'summary': summary_result,
                'content_preview': content[:200] + '...' if len(content) > 200 else content,
                'image_path': image_path
            }
        except Exception as e:
            logging.error(f"Error analyzing {chapter_path}: {str(e)}")
            self.metrics['errors'] += 1
            return None

    def generate_report(self, analyses, output_file='reports/chapter_summary_report.md'):
        """Generate markdown report from chapter analyses."""
        report = """# Chapter Summary Report

## Author Context
The author's life events primarily occurred in:
- Canada's North (Yukon, Northwest Territories)
- Alaska
- Ontario (childhood)
- Alberta and Northern BC

## Overview
- Chapters processed: {processed}
- Analysis errors: {errors}
- Chapters with missing locations: {missing_locations}

## Chapter Details
""".format(
    processed=self.metrics['chapters_processed'],
    errors=self.metrics['errors'],
    missing_locations=self.metrics['missing_locations']
)

        for i, (chapter_path, analysis) in enumerate(analyses.items(), 1):
            if not analysis:
                report += f"\n### Chapter {i}: Analysis Failed\n"
                continue
                
            report += f"""
### Chapter {i}: {os.path.basename(chapter_path)}

**Estimated Year**: {analysis['date'].get('year', 'unknown')}
**Confidence**: {analysis['date'].get('confidence', 0)}
**Date Reasoning**: {analysis['date'].get('reasoning', '')}

**Location**: {analysis['location'].get('location', {}).get('name', 'unknown')}
**Coordinates**: {analysis['location'].get('location', {}).get('coordinates', 'unknown')}
**Location Evidence**:
{analysis['location'].get('location', {}).get('reasoning', 'No specific location evidence found')}

**Geographical Context**:
{analysis['location'].get('location', {}).get('context', 'Northern Canada region')}

**Summary**:
{analysis['summary'].get('summary', 'No summary available')}

{'![Chapter Illustration](../' + analysis['image_path'] + ')' if analysis.get('image_path') else ''}

**Preview**:
{analysis['content_preview']}

---
"""
        Path(output_file).parent.mkdir(exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

def main():
    """Main execution function."""
    chapter_dir = 'chapters'  # Chapters are in the current directory
    if not os.path.exists(chapter_dir):
        print(f"Error: {chapter_dir} directory not found", file=sys.stderr)
        return 1

    analyzer = ChapterAnalysis()
    analyses = {}
    
    # Process each chapter file
    chapter_files = sorted([f for f in os.listdir(chapter_dir) if f.endswith('.txt')])
    total_chapters = len(chapter_files)
    logging.info(f"Found {total_chapters} chapters to process")
    
    for i, chapter_file in enumerate(chapter_files, 1):
        progress = f"[{i}/{total_chapters} - {int((i/total_chapters)*100)}%]"
        print(f"\n{progress} Processing: {chapter_file}")
        logging.info(f"\nProcessing chapter {i}/{total_chapters}: {chapter_file}")
        
        analysis = analyzer.analyze_chapter(chapter_file, chapter_dir)
        analyses[os.path.join(chapter_dir, chapter_file)] = analysis
        
        if analysis:
            print(f"  Date: {analysis['date'].get('year', 'unknown')}")
            print(f"  Location: {analysis['location'].get('location', {}).get('name', 'unknown')}")
            print(f"  Summary: {analysis['summary'].get('summary', 'No summary available')}")
        
        if analysis:
            logging.info(f"Chapter {i} results:")
            logging.info(f"  Date: {analysis['date'].get('year', 'unknown')}")
            logging.info(f"  Location: {analysis['location'].get('location', {}).get('name', 'unknown')}")
            logging.info(f"  Summary: {analysis['summary'].get('summary', 'No summary available')}")
        else:
            print("  Analysis failed for this chapter")
    
    # Generate report
    analyzer.generate_report(analyses)
    print(f"Report generated with {analyzer.metrics['chapters_processed']} chapters analyzed")
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())