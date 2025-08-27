import cv2
import numpy as np
import os
import sys
import json

# Configuration
A4_WIDTH = 3508
A4_HEIGHT = 2480
BUBBLE_THRESHOLD = 0.5
QUESTION_BAR_RATIO = 0.2

# Section coordinates (x1, y1, x2, y2)
SECTIONS = {
    1: (344, 608, 1861, 896), 2: (356, 972, 1855, 1232), 3: (341, 1311, 1855, 1562), 4: (334, 1661, 1848, 1921),
    5: (337, 2017, 1848, 2278), 6: (1904, 1318, 3403, 1568), 7: (1889, 1664, 3427, 1931), 8: (1901, 2022, 3393, 2282)
}

def detect_creases(img, edges):
    """Detect if the paper has creases that might interfere with cropping"""
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=200)
    if lines is None:
        return False, "No significant lines detected"
    
    crease_indicators = []
    for line in lines[:20]:  # Check first 20 lines
        rho, theta = line[0]
        # Check for near-horizontal or vertical lines (creases)
        if (abs(theta) < 0.2 or abs(theta - np.pi) < 0.2 or abs(theta - np.pi/2) < 0.2):
            crease_indicators.append(f"Line at angle {theta:.2f}")
    
    if len(crease_indicators) > 5:
        return True, f"Detected {len(crease_indicators)} potential crease lines"
    return False, "No creases detected"

def validate_paper_shape(approx, contour_area, img_area):
    """Validate if the detected paper shape is reasonable"""
    issues = []
    
    # Check corners
    if len(approx) != 4:
        issues.append(f"Paper has {len(approx)} corners instead of 4 (may be creased)")
    
    # Check area ratio
    area_ratio = contour_area / img_area
    if area_ratio < 0.3:
        issues.append(f"Paper too small ({area_ratio:.2f} of image) - may be folded")
    elif area_ratio > 0.95:
        issues.append(f"Paper too large ({area_ratio:.2f} of image) - detection error")
    
    # Check corner angles for severe distortion
    if len(approx) == 4:
        corners = approx.reshape(4, 2)
        for i in range(4):
            p1, p2, p3 = corners[i], corners[(i + 1) % 4], corners[(i + 2) % 4]
            v1, v2 = p1 - p2, p3 - p2
            cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            angle = np.arccos(np.clip(cos_angle, -1, 1)) * 180 / np.pi
            if angle < 60 or angle > 120:
                issues.append(f"Corner {i+1} suspicious angle: {angle:.1f}° (folding)")
    
    return issues

def load_and_crop_paper(image_path):
    """Load image and extract paper with perspective correction and crease detection"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image from {image_path}")
    
    print(f"Processing image: {image_path}")
    img_area = img.shape[0] * img.shape[1]

    # Edge detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    
    # Check for creases
    has_creases, crease_info = detect_creases(img, edges)
    if has_creases:
        print(f"⚠️  WARNING: {crease_info}")
        print("   This may cause cropping issues. Consider flattening the paper.")
    
    # Find paper contour
    kernel = np.ones((5,5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("❌ ERROR: No paper detected in the image")
    
    page_contour = max(contours, key=cv2.contourArea)
    contour_area = cv2.contourArea(page_contour)
    peri = cv2.arcLength(page_contour, True)
    approx = cv2.approxPolyDP(page_contour, 0.02 * peri, True)
    
    # Validate paper shape
    shape_issues = validate_paper_shape(approx, contour_area, img_area)
    if shape_issues:
        error_msg = "❌ ERROR: Paper appears to be creased or folded:\n"
        for issue in shape_issues:
            error_msg += f"   • {issue}\n"
        error_msg += "   Please flatten the paper and try again."
        raise ValueError(error_msg)
    
    # Get corners and order them
    if len(approx) == 4:
        corners = approx.reshape(4, 2)
        print("✅ Successfully detected 4-corner paper shape")
    else:
        print("⚠️  Using bounding rectangle (paper shape not perfectly rectangular)")
        x, y, w, h = cv2.boundingRect(page_contour)
        corners = np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]], dtype=np.float32)
    
    # Order points: top-left, top-right, bottom-right, bottom-left
    rect = np.zeros((4, 2), dtype=np.float32)
    s = corners.sum(axis=1)
    rect[0] = corners[np.argmin(s)]  # top-left
    rect[2] = corners[np.argmax(s)]  # bottom-right
    diff = np.diff(corners, axis=1)
    rect[1] = corners[np.argmin(diff)]  # top-right
    rect[3] = corners[np.argmax(diff)]  # bottom-left
    
    # Check for extreme perspective distortion
    distances = [np.linalg.norm(rect[i] - rect[(i + 1) % 4]) for i in range(4)]
    ratio1 = distances[0] / distances[2] if distances[2] > 0 else 1
    ratio2 = distances[1] / distances[3] if distances[3] > 0 else 1
    
    if ratio1 > 2 or ratio1 < 0.5 or ratio2 > 2 or ratio2 < 0.5:
        raise ValueError(f"❌ ERROR: Severe paper distortion (ratios: {ratio1:.2f}, {ratio2:.2f})\n"
                        "   This usually indicates creases or folds. Please flatten the paper.")
    
    # Apply perspective transform
    dst = np.array([[0, 0], [A4_WIDTH - 1, 0], [A4_WIDTH - 1, A4_HEIGHT - 1], [0, A4_HEIGHT - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (A4_WIDTH, A4_HEIGHT))
    
    print("✅ Paper cropping completed successfully")
    return warped

def normalize_section(section_img, target_width=1500, target_height=300):
    """Normalize section to consistent size"""
    h, w = section_img.shape[:2]
    
    # Create white background and scale to fit
    normalized = np.ones((target_height, target_width, 3), dtype=np.uint8) * 255
    scale = min(target_width / w, target_height / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(section_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Center on canvas
    y_offset = (target_height - new_h) // 2
    x_offset = (target_width - new_w) // 2
    normalized[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    
    return normalized

def find_bubble_positions(bubble_area):
    """Find actual bubble positions using contour detection with fallback"""
    _, thresh = cv2.threshold(bubble_area, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        # Fallback to equal division
        height = bubble_area.shape[0]
        bubble_height = height // 4
        return [(0, i * bubble_height, bubble_area.shape[1], 
                (i + 1) * bubble_height if i < 3 else height) for i in range(4)]
    
    # Filter contours by area and aspect ratio
    bubble_contours = []
    min_area = 100
    max_area = bubble_area.shape[0] * bubble_area.shape[1] // 6
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_area < area < max_area:
            x, y, w, h = cv2.boundingRect(contour)
            if 0.3 < (w / h if h > 0 else 0) < 3.0:
                bubble_contours.append((x, y, w, h, area))
    
    # Sort by y-coordinate and take top 4
    bubble_contours.sort(key=lambda b: b[1])
    if len(bubble_contours) > 4:
        bubble_contours = sorted(bubble_contours, key=lambda b: b[4], reverse=True)[:4]
        bubble_contours.sort(key=lambda b: b[1])
    
    if len(bubble_contours) < 4:
        # Fallback to equal division
        height = bubble_area.shape[0]
        bubble_height = height // 4
        return [(0, i * bubble_height, bubble_area.shape[1], 
                (i + 1) * bubble_height if i < 3 else height) for i in range(4)]
    
    return [(x, y, x + w, y + h) for x, y, w, h, _ in bubble_contours[:4]]

def detect_marked_bubble(column_img, save_debug=False, debug_dir=None, question_num=None, section_num=None):
    """Detect which bubble (1-4) is marked, return 0 if none"""
    gray = cv2.cvtColor(column_img, cv2.COLOR_BGR2GRAY) if len(column_img.shape) == 3 else column_img
    
    # Remove question number bar
    question_bar_height = int(gray.shape[0] * QUESTION_BAR_RATIO)
    bubble_area = gray[question_bar_height:, :]
    bubble_area_color = column_img[question_bar_height:, :]
    
    # Find bubble positions and apply threshold
    bubble_positions = find_bubble_positions(bubble_area)
    _, thresh = cv2.threshold(bubble_area, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    bubble_scores = []
    for bubble_num, (x1, y1, x2, y2) in enumerate(bubble_positions, 1):
        bubble_region = thresh[y1:y2, x1:x2]
        
        # Calculate fill score
        total_pixels = bubble_region.size
        white_pixels = np.sum(bubble_region == 0)  # Unfilled area
        black_pixels = np.sum(bubble_region == 255)  # Filled area
        
        white_ratio = white_pixels / total_pixels if total_pixels > 0 else 1.0
        black_ratio = black_pixels / total_pixels if total_pixels > 0 else 0.0
        
        fill_score = 1.0 - white_ratio  # Higher = more filled
        if black_ratio < 0.1:  # Too few black pixels = likely empty
            fill_score = 0.0
        
        bubble_scores.append((bubble_num, fill_score))
        
        # Save debug images
        if save_debug and debug_dir and question_num and section_num:
            bubble_color = bubble_area_color[y1:y2, x1:x2]
            bubble_file = os.path.join(debug_dir, f"s{section_num}_q{question_num:02d}_bubble_{bubble_num}_fill_{fill_score:.3f}.jpg")
            thresh_file = os.path.join(debug_dir, f"s{section_num}_q{question_num:02d}_bubble_{bubble_num}_thresh_w{white_ratio:.3f}_b{black_ratio:.3f}.jpg")
            cv2.imwrite(bubble_file, bubble_color, [cv2.IMWRITE_JPEG_QUALITY, 100])
            cv2.imwrite(thresh_file, bubble_region, [cv2.IMWRITE_JPEG_QUALITY, 100])
    
    # Find best bubble
    bubble_scores.sort(key=lambda x: x[1], reverse=True)
    best_bubble, best_score = bubble_scores[0]
    
    return best_bubble if best_score > BUBBLE_THRESHOLD else 0

def process_section(warped_img, section_num, sections_dir, save_debug=False):
    """Process a single section: normalize, extract columns, detect bubbles"""
    x1, y1, x2, y2 = SECTIONS[section_num]
    
    # Extract, normalize and save section
    raw_section = warped_img[y1:y2, x1:x2]
    normalized_section = normalize_section(raw_section)
    section_path = os.path.join(sections_dir, f"section_{section_num}.jpg")
    cv2.imwrite(section_path, normalized_section, [cv2.IMWRITE_JPEG_QUALITY, 100])
    
    # Create directories
    columns_dir = os.path.join(sections_dir, f"section_{section_num}_columns")
    os.makedirs(columns_dir, exist_ok=True)
    debug_dir = None
    if save_debug:
        debug_dir = os.path.join(sections_dir, f"section_{section_num}_bubbles_analysis")
        os.makedirs(debug_dir, exist_ok=True)
    
    # Process 30 columns
    height, width = normalized_section.shape[:2]
    column_width = width // 30
    section_answers = {}
    
    for col in range(30):
        x1_col = col * column_width
        x2_col = min(x1_col + column_width if col < 29 else width, width)
        
        column_img = normalized_section[:, x1_col:x2_col]
        question_num = col + 1
        
        # Detect marked bubble and save column
        marked_bubble = detect_marked_bubble(column_img, save_debug, debug_dir, question_num, section_num)
        section_answers[question_num] = marked_bubble
        
        column_path = os.path.join(columns_dir, f"column_{question_num:02d}.jpg")
        cv2.imwrite(column_path, column_img, [cv2.IMWRITE_JPEG_QUALITY, 100])
    
    return section_path, section_answers

def process_answer_sheet(image_path, save_debug=False):
    """Main processing function"""
    # Load and crop paper
    warped = load_and_crop_paper(image_path)
    
    # Create results and sections directories
    results_dir = "results"
    sections_dir = "sections"
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(sections_dir, exist_ok=True)
    
    # Save cropped page
    cropped_path = os.path.join(results_dir, "cropped_page.jpg")
    cv2.imwrite(cropped_path, warped, [cv2.IMWRITE_JPEG_QUALITY, 100])
    print(f"Saved cropped page as '{cropped_path}'")
    
    # Process all sections
    all_answers = {}
    extracted_files = []
    
    for section_num in range(1, 9):
        print(f"Processing section {section_num}...")
        section_path, section_answers = process_section(warped, section_num, sections_dir, save_debug)
        extracted_files.append(section_path)
        all_answers[f"section_{section_num}"] = section_answers
        
        # Show sample answers
        sample_answers = dict(list(section_answers.items())[:5])
        print(f"  Sample answers: {sample_answers}...")
    
    return extracted_files, all_answers, cropped_path

def main():
    """Main execution function"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get image path
    image_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(script_dir, "answersheet.jpg")
    
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found.")
        print("Usage: python psy.py [path_to_image]")
        sys.exit(1)
    
    try:
        # Process with debug images enabled
        extracted_files, all_answers, cropped_path = process_answer_sheet(image_path, save_debug=True)
        
        # Print summary
        print(f"\n=== SUMMARY ===")
        print(f"Successfully processed {len(extracted_files)} sections")
        print(f"Cropped page saved: {cropped_path}")
        print(f"Extracted 240 bubble columns total (8 sections × 30 questions)")
        print(f"Saved bubble analysis images in section_X_bubbles_analysis/ directories")
        
        # Print detected answers
        print(f"\n=== DETECTED ANSWERS ===")
        for section_name, answers in all_answers.items():
            print(f"\n{section_name.upper()}:")
            for i in range(0, 30, 10):
                group = {k: v for k, v in answers.items() if i < k <= i + 10}
                print(f"  Questions {i+1}-{i+10}: {group}")
        
        # Save answers to JSON
        with open("detected_answers.json", "w") as f:
            json.dump(all_answers, f, indent=2)
        print(f"\nAnswers saved to: detected_answers.json")
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
