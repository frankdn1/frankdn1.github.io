# Static Site Implementation Tasks: Frank Dunn - Memoirs of the North

This document breaks down the tasks required to implement the static website based on the `static_site_architecture_plan.md`.

## Phase 1: Setup & Prerequisite Generation

*   **Task 1.1: Verify/Run Chapter Extraction:**
    *   Ensure `chapters/*.txt` files are up-to-date.
    *   If `book.txt` has changed, run `python scripts/extract_chapters.py`.
*   **Task 1.2: Configure LLM Environment:**
    *   Set up necessary API keys/environment variables for `llm_analyzer.py`.
*   **Task 1.3: Run Content Analysis & Asset Generation:**
    *   Execute `python scripts/analyze_chapters.py`.
    *   Verify generation of `reports/chapter_summary_report.md` and `assets/images/*.png`.
*   **Task 1.4: Run Date Analysis:**
    *   Execute `python scripts/analyze_chapter_dates.py`.
    *   Verify generation of `reports/chapter_dates_report.md`.

## Phase 2: Build Script Core Logic (`build.py`)

*   **Task 2.1: Initialize Build Script:**
    *   Create `build.py`.
    *   Add basic structure and argument parsing (e.g., for specifying output directory).
*   **Task 2.2: Implement Report Parsing:**
    *   Add functions to `build.py` to read and parse data from:
        *   `reports/chapter_summary_report.md`
        *   `reports/chapter_dates_report.md`
        *   Directory listing of `chapters/*.txt`
*   **Task 2.3: Implement Search Index Generation:**
    *   Add logic to `build.py` to create `search-index.json` using parsed report data (title, summary, keywords, etc.) suitable for Fuse.js.

## Phase 3: Templating & HTML Generation

*   **Task 3.1: Integrate Templating Engine:**
    *   Choose and install a Python templating engine (e.g., `pip install Jinja2`).
    *   Set up the templating environment within `build.py`.
*   **Task 3.2: Create Base HTML Templates:**
    *   Develop base templates (`templates/base.html`) including common header, footer, sidebar structure using HTML and Tailwind CSS utility classes.
*   **Task 3.3: Create Page Templates:**
    *   Develop specific templates for each page type:
        *   `templates/index.html` (Homepage)
        *   `templates/map.html` (Map view)
        *   `templates/timeline.html` (Timeline view)
        *   `templates/chapters_index.html` (Chapter listing)
        *   `templates/chapter_detail.html` (Individual chapter)
        *   (Optional) `templates/theme_index.html`, `templates/theme_detail.html`
*   **Task 3.4: Implement HTML Generation Logic:**
    *   Add logic to `build.py` to iterate through parsed data and render the templates into static HTML files in the output directory (e.g., `dist/`). Ensure correct file naming (e.g., `dist/chapters/[slug].html`).

## Phase 4: Styling & Asset Processing

*   **Task 4.1: Set up Tailwind CSS:**
    *   Initialize Tailwind CSS (`npx tailwindcss init`).
    *   Configure `tailwind.config.js` and input CSS file.
*   **Task 4.2: Implement CSS Compilation:**
    *   Add a step in `build.py` to run the Tailwind CLI build command (`npx tailwindcss -i ./path/to/input.css -o ./dist/assets/css/styles.css --minify`) targeting the generated HTML/template files.
*   **Task 4.3: Implement Image Optimization:**
    *   Choose an image optimization tool (Sharp CLI or Python Pillow).
    *   Add a step in `build.py` to process images from `assets/images/` into optimized formats (WebP/AVIF) and sizes, placing them in `dist/assets/images/`.
*   **Task 4.4: Implement Asset Copying:**
    *   Add logic to `build.py` to copy necessary static assets to the `dist/` directory:
        *   Compiled CSS (`dist/assets/css/styles.css`)
        *   JavaScript libraries (Leaflet, Fuse.js, vis-timeline, etc.)
        *   Optimized images (`dist/assets/images/`)
        *   Chapter audio files (`*.mp3` -> `dist/assets/audio/`)
        *   `search-index.json` (`dist/assets/data/`)
        *   Any other required static files (e.g., fonts).

## Phase 5: Feature Implementation (Static Adaptations)

*   **Task 5.1: Implement Global Layout & Basic JS:**
    *   Refine HTML structure in base templates.
    *   Add Vanilla JS for mobile sidebar drawer toggle and theme switching.
*   **Task 5.2: Implement Map Page (`map.html`):**
    *   Integrate Leaflet.js library.
    *   Write JS to parse location data (from build script, perhaps embedded JSON).
    *   Generate markers statically, add clustering (Leaflet.markercluster).
    *   Link markers to corresponding `chapters/[slug].html` pages.
*   **Task 5.3: Implement Timeline Page (`timeline.html`):**
    *   Integrate vis-timeline.js (or build custom HTML/CSS timeline).
    *   Write JS to parse date data (from build script, perhaps embedded JSON).
    *   Populate the timeline statically.
    *   Link timeline items to corresponding `chapters/[slug].html` pages.
*   **Task 5.4: Implement Chapters Index Page (`chapters/index.html`):**
    *   Ensure the build script generates the static grid of chapter cards.
    *   Add basic client-side filtering/sorting JS if desired.
    *   Decide and implement pagination (multiple static pages or client-side JS).
*   **Task 5.5: Implement Chapter Detail Page (`chapters/[slug].html`):**
    *   Ensure templates correctly display full text, banner, breadcrumb.
    *   Integrate a JS Lightbox library for the image gallery.
    *   Integrate HTML5 `<audio>` player and add basic JS controls (play/pause/skip).
*   **Task 5.6: Implement Search:**
    *   Add search input to the header template.
    *   Integrate Fuse.js library.
    *   Write JS to fetch `search-index.json`, initialize Fuse, handle user input, and display results.
*   **Task 5.7: Implement Audio Narration Integration:**
    *   Ensure audio files (`<slug>-narration.mp3`) are correctly copied during the build.
    *   Verify the HTML5 player works on chapter pages.
    *   Decide on and implement transcript display strategy (if any).
*   **Task 5.8: (Optional) Implement Thematic Collections:**
    *   Define theme metadata (manual or LLM-assisted during analysis).
    *   Update `build.py` and templates to generate theme index/detail pages.

## Phase 6: Finalization & Deployment Prep

*   **Task 6.1: Performance & Accessibility Audit:**
    *   Run Lighthouse checks on key pages.
    *   Perform manual accessibility testing (keyboard navigation, screen reader).
    *   Optimize images, CSS, JS further based on findings.
*   **Task 6.2: Build Script Refinement:**
    *   Add error handling, logging, and comments to `build.py`.
    *   Ensure the script is idempotent where possible.
*   **Task 6.3: Documentation:**
    *   Update `README.md` with instructions on how to run the build process and prerequisites.
*   **Task 6.4: Deployment Configuration:**
    *   Set up GitHub Actions workflow (or manual process) to:
        *   Run the `build.py` script.
        *   Deploy the contents of the `dist/` directory to the `gh-pages` branch (or configured GitHub Pages source).