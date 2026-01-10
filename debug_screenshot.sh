#!/bin/bash
# Debug Screenshot Tool for Claude Code
# Optimizes screenshots to reduce token usage

set -e

SCRIPT_NAME="debug_screenshot.sh"
VERSION="1.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Debug Screenshot Tool v${VERSION}"
    echo "  Optimize screenshots for Claude Code debugging"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Usage: $SCRIPT_NAME [input_image] [options]"
    echo ""
    echo "Options:"
    echo "  --width WIDTH    Resize to width (default: 800px)"
    echo "  --quality Q      JPEG quality 1-100 (default: 85)"
    echo "  --ocr            Extract text with tesseract (if installed)"
    echo "  --crop WxH+X+Y   Crop to region (e.g., 800x600+100+50)"
    echo "  --console        Optimized for console text (high contrast)"
    echo ""
    echo "Examples:"
    echo "  $SCRIPT_NAME screenshot.png"
    echo "  $SCRIPT_NAME error.png --width 600 --ocr"
    echo "  $SCRIPT_NAME fullscreen.png --crop 1024x768+0+0"
    echo "  $SCRIPT_NAME console.png --console --ocr"
    echo ""
    echo "Output:"
    echo "  - Optimized image: screenshot_optimized.jpg"
    echo "  - Extracted text (if --ocr): screenshot_text.txt"
    echo "  - Token estimate and recommendations"
    echo ""
}

# Default settings
WIDTH=800
QUALITY=85
DO_OCR=false
CROP=""
CONSOLE_MODE=false

# Check for required tools
check_dependencies() {
    local missing=""

    if ! command -v convert &> /dev/null; then
        missing="${missing}imagemagick "
    fi

    if [[ "$DO_OCR" == true ]] && ! command -v tesseract &> /dev/null; then
        echo -e "${YELLOW}Warning: tesseract not installed, OCR disabled${NC}"
        echo "Install with: sudo apt-get install tesseract-ocr"
        DO_OCR=false
    fi

    if [[ -n "$missing" ]]; then
        echo -e "${RED}Error: Missing required tools: $missing${NC}"
        echo ""
        echo "Install with:"
        echo "  sudo apt-get install imagemagick tesseract-ocr"
        exit 1
    fi
}

# Parse arguments
if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    print_usage
    exit 0
fi

INPUT_FILE="$1"
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --width)
            WIDTH="$2"
            shift 2
            ;;
        --quality)
            QUALITY="$2"
            shift 2
            ;;
        --ocr)
            DO_OCR=true
            shift
            ;;
        --crop)
            CROP="$2"
            shift 2
            ;;
        --console)
            CONSOLE_MODE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Validate input file
if [[ ! -f "$INPUT_FILE" ]]; then
    echo -e "${RED}Error: File not found: $INPUT_FILE${NC}"
    exit 1
fi

# Get file info
FILESIZE=$(stat -f%z "$INPUT_FILE" 2>/dev/null || stat -c%s "$INPUT_FILE")
FILESIZE_KB=$((FILESIZE / 1024))
DIMENSIONS=$(identify -format "%wx%h" "$INPUT_FILE")

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Processing: $INPUT_FILE${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Original size: ${FILESIZE_KB}KB ($DIMENSIONS)"
echo ""

check_dependencies

# Generate output filename
BASENAME=$(basename "$INPUT_FILE" | sed 's/\.[^.]*$//')
OUTPUT_IMAGE="${BASENAME}_optimized.jpg"
OUTPUT_TEXT="${BASENAME}_text.txt"

# Build ImageMagick command
CMD="convert \"$INPUT_FILE\""

# Crop if specified
if [[ -n "$CROP" ]]; then
    CMD="$CMD -crop $CROP +repage"
    echo "Cropping to: $CROP"
fi

# Resize
CMD="$CMD -resize ${WIDTH}x"
echo "Resizing to width: ${WIDTH}px"

# Console mode optimizations
if [[ "$CONSOLE_MODE" == true ]]; then
    echo "Console mode: enhancing text contrast"
    CMD="$CMD -normalize -contrast-stretch 0"
    QUALITY=95  # Higher quality for text
fi

# Set quality and output
CMD="$CMD -quality $QUALITY \"$OUTPUT_IMAGE\""

# Execute conversion
echo ""
echo -e "${GREEN}Optimizing image...${NC}"
eval $CMD

# Get output size
OUTPUT_SIZE=$(stat -f%z "$OUTPUT_IMAGE" 2>/dev/null || stat -c%s "$OUTPUT_IMAGE")
OUTPUT_SIZE_KB=$((OUTPUT_SIZE / 1024))
OUTPUT_DIMENSIONS=$(identify -format "%wx%h" "$OUTPUT_IMAGE")

echo -e "${GREEN}✓ Image optimized: $OUTPUT_IMAGE${NC}"
echo "  Size: ${OUTPUT_SIZE_KB}KB ($OUTPUT_DIMENSIONS)"
echo "  Reduction: $((100 - (OUTPUT_SIZE * 100 / FILESIZE)))%"

# OCR if requested
if [[ "$DO_OCR" == true ]]; then
    echo ""
    echo -e "${GREEN}Extracting text with OCR...${NC}"

    tesseract "$OUTPUT_IMAGE" "${BASENAME}_text" -l eng 2>/dev/null

    if [[ -f "$OUTPUT_TEXT" ]]; then
        WORD_COUNT=$(wc -w < "$OUTPUT_TEXT")
        echo -e "${GREEN}✓ Text extracted: $OUTPUT_TEXT${NC}"
        echo "  Words: $WORD_COUNT"

        # Show preview
        echo ""
        echo "━━━━━━━━━━━━━━━━ Extracted Text Preview ━━━━━━━━━━━━━━━━"
        head -20 "$OUTPUT_TEXT"
        if [[ $(wc -l < "$OUTPUT_TEXT") -gt 20 ]]; then
            echo "... (truncated, see $OUTPUT_TEXT for full text)"
        fi
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
fi

# Token estimation
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  Token Usage Estimates${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Rough estimates based on image processing
ORIGINAL_TOKENS=$((FILESIZE / 1000))  # Very rough estimate
OPTIMIZED_TOKENS=$((OUTPUT_SIZE / 1000))

echo "Original image:   ~${ORIGINAL_TOKENS} tokens"
echo "Optimized image:  ~${OPTIMIZED_TOKENS} tokens"

if [[ "$DO_OCR" == true ]] && [[ -f "$OUTPUT_TEXT" ]]; then
    TEXT_TOKENS=$((WORD_COUNT / 3))  # Rough: 1 token ≈ 3-4 words
    echo "Extracted text:   ~${TEXT_TOKENS} tokens"
    echo ""
    echo -e "${GREEN}✓ BEST OPTION: Copy/paste extracted text${NC}"
    echo "  (Uses ~${TEXT_TOKENS} tokens instead of ~${OPTIMIZED_TOKENS})"
fi

echo ""
echo -e "${YELLOW}Recommendations:${NC}"
if [[ "$DO_OCR" == true ]] && [[ -f "$OUTPUT_TEXT" ]]; then
    echo "  1. Send extracted text file (most efficient)"
    echo "  2. Send optimized image if visual context needed"
else
    echo "  1. Send optimized image ($OUTPUT_IMAGE)"
    echo "  2. Use --ocr flag if image contains text/console output"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
