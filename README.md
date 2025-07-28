# PDF Outline Extractor

A sophisticated PDF document structure extraction tool that intelligently identifies titles and hierarchical headings (H1, H2, H3) from PDF documents.

## Approach

This solution uses a multi-layered approach to accurately extract document structure:

### 1. Title Extraction
- Analyzes the first page to identify the document title
- Uses font size analysis and positioning to distinguish titles from regular text
- Implements smart deduplication to handle multi-line titles
- Handles edge cases like repeated title elements

### 2. Heading Detection
Our heading detection combines multiple techniques:

#### Formatting-Based Detection
- Font size analysis relative to document average
- Bold text detection using PDF formatting flags
- Position-based filtering (excludes headers, footers, margins)

#### Pattern-Based Detection
- Numbered sections (1., 1.1, 1.1.1, etc.)
- Named sections (Chapter, Part, Appendix, etc.)
- All-caps headings
- Multilingual heading patterns (supports 8+ languages)

#### Advanced Filtering
- Table of contents detection and exclusion
- Form field filtering (signatures, dates, addresses)
- List sequence detection to avoid false positives
- Table content exclusion using pdfplumber
- Text direction compatibility (RTL support for Arabic)

### 3. Multilingual Support (Bonus Feature)
Our solution includes comprehensive multilingual capabilities:
- **Language Detection**: Unicode script analysis for 8 major writing systems
- **Cultural Adaptations**: Right-to-left text support, CJK character handling
- **Multilingual Patterns**: Language-specific heading keywords and structures
- **Supported Languages**: English, Japanese, Chinese, Russian, Arabic, German, Spanish, French, Korean

## Libraries Used

### Core Dependencies
- **PyMuPDF (fitz)**: Primary PDF parsing and text extraction
  - Size: ~50MB
  - Provides detailed font, positioning, and formatting information
  - Handles complex PDF structures and encodings

- **pdfplumber**: Table detection and validation
  - Size: ~10MB
  - Ensures headings aren't extracted from table content
  - Provides precise bounding box information

### Total Model/Library Size
- Combined library size: ~60MB (well under 200MB limit)
- No external ML models used
- Pure algorithmic approach with rule-based intelligence

## Technical Features

### Performance Optimizations
- Processes documents in under 10 seconds for 50-page PDFs
- Memory-efficient streaming processing
- Optimized font size calculations using sampling

### Robustness Features
- Handles malformed PDFs gracefully
- Supports rotated and skewed text
- Manages various PDF encodings and character sets
- Processes both scanned and native PDF content

### Quality Assurance
- Smart duplicate removal
- Text artifact cleanup
- Heading level validation
- Page number accuracy (1-based indexing)

## How to Build and Run

### Building the Docker Image
```bash
docker build --platform linux/amd64 -t pdf-extractor:latest .
```

### Running the Solution
```bash
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-extractor:latest
```

### Expected Behavior
- Automatically processes all PDF files in `/app/input`
- Generates corresponding JSON files in `/app/output`
- Each `filename.pdf` produces `filename.json`
- No internet connectivity required (offline operation)

## Output Format

```json
{
  "title": "Document Title",
  "outline": [
    { "level": "H1", "text": "Chapter 1: Introduction", "page": 1 },
    { "level": "H2", "text": "Background", "page": 2 },
    { "level": "H3", "text": "Related Work", "page": 3 }
  ]
}
```

## Competitive Advantages

1. **High Accuracy**: Combines multiple detection methods for robust results
2. **Multilingual Support**: Handles global documents with cultural awareness
3. **Performance**: Meets strict timing requirements with efficient algorithms
4. **Reliability**: Extensive filtering prevents false positive headings
5. **Scalability**: Modular design ready for Round 1B extensions

## Architecture

The solution is built with modularity in mind:
- `PDFOutlineExtractor`: Main extraction class
- Separate methods for title extraction, heading detection, and filtering
- Language detection and multilingual pattern matching
- Table detection integration
- Configurable formatting thresholds

This foundation enables easy extension for semantic search, recommendation systems, and advanced document understanding in subsequent rounds.
