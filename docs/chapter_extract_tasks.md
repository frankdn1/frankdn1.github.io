# Chapter Extraction Tasks

## 1. Setup Tasks
- [ ] Create a `chapters` directory if it doesn't exist
- [ ] Verify `book.txt` exists and is accessible

## 2. Table of Contents Parsing
- [ ] Read and parse the table of contents from the top of `book.txt`
- [ ] Extract chapter titles and numbers while ignoring page numbers
- [ ] Handle tab-separated format of TOC entries

## 3. Chapter Extraction
- [ ] For each chapter in TOC:
  - [ ] Locate chapter start (chapter title as heading)
  - [ ] Extract content until next chapter title (or end of file for last chapter)
  - [ ] Preserve all content including multi-line paragraphs

## 4. File Naming & Sanitization
- [ ] For each chapter:
  - [ ] Format chapter number with leading zeros (01, 02, etc.)
  - [ ] Sanitize title by:
    - Replacing spaces with underscores
    - Removing special characters (periods, quotes, commas, etc.)
    - Handling edge cases like ".219" in "The Story Of The .219 Zipper Improved Rifle"
  - [ ] Create filename in format: `NN_Chapter_Title.txt`

## 5. File Output
- [ ] For each extracted chapter:
  - [ ] Write content to corresponding file in `chapters/` directory
  - [ ] Verify file was created successfully

## 6. Edge Case Handling
- [ ] Ensure proper handling of:
  - Chapters with punctuation in titles (. ' , )
  - Titles containing numbers (e.g., ".219")
  - Multi-line chapter content preservation
  - Last chapter extraction (no next title)
  - Apostrophes in titles (e.g., "John’s")
  - Maximum filename length (truncate at 255 chars)

## 7. Error Handling
- [ ] Implement recovery for:
  - Malformed TOC entries (log and skip)
  - Missing chapter start markers
  - File write failures (retry 3 times)
  - Interrupted processing (save progress)
- [ ] Validate UTF-8 encoding for all files

## 8. Verification
- [ ] Confirm all 36 chapters from the TOC were processed
- [ ] Verify each output file:
  - Has correct naming format
  - Contains complete chapter content
  - Is properly placed in `chapters/` directory
  - Valid UTF-8 encoding
  - Non-zero file size
- [ ] Perform checksum comparison of source vs extracted content
- [ ] Validate chapter count matches TOC entries

## 9. Completion Check
- [ ] Final verification that all tasks from chapter_extract.md are complete
- [ ] Ensure no chapter content was lost or misassigned
- [ ] Generate summary report with:
  - Processing statistics
  - Error log review
  - Storage space verification