import cv2
import numpy as np
import os

def preprocess_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image from {image_path}")
    return img

def find_page_corners(img):
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Use Canny edge detection
    edges = cv2.Canny(blur, 50, 150)
    
    # Dilate the edges to connect them
    kernel = np.ones((5,5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the largest contour
    if not contours:
        raise ValueError("No contours found in the image")
    
    # Sort contours by area and get the largest one
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    page_contour = contours[0]
    
    # Approximate the contour to get a polygon
    peri = cv2.arcLength(page_contour, True)
    approx = cv2.approxPolyDP(page_contour, 0.02 * peri, True)
    
    # Draw the contour and corners on a copy of the image for debugging
    debug_img = img.copy()
    cv2.drawContours(debug_img, [page_contour], -1, (0, 255, 0), 2)
    
    # If we have 4 points, we have a rectangle
    if len(approx) == 4:
        corners = approx.reshape(4, 2)
        # Draw the corners
        for corner in corners:
            x, y = corner
            cv2.circle(debug_img, (int(x), int(y)), 5, (0, 0, 255), -1)
        cv2.imwrite("debug_corners.jpg", debug_img)
        return corners
    else:
        # If we don't have 4 points, use the bounding rectangle
        x, y, w, h = cv2.boundingRect(page_contour)
        corners = np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]], dtype=np.float32)
        # Draw the corners
        for corner in corners:
            x, y = corner
            cv2.circle(debug_img, (int(x), int(y)), 5, (0, 0, 255), -1)
        cv2.imwrite("debug_corners.jpg", debug_img)
        return corners

def order_points(pts):
    # Initialize a list of coordinates that will be ordered
    rect = np.zeros((4, 2), dtype=np.float32)
    
    # The top-left point will have the smallest sum
    # The bottom-right point will have the largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # The top-right point will have the smallest difference
    # The bottom-left will have the largest difference
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def four_point_transform(image, pts):
    # Obtain a consistent order of the points
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    # A4 dimensions at 300 DPI (landscape orientation)
    A4_WIDTH = 3508  # Swapped with height for landscape
    A4_HEIGHT = 2480  # Swapped with width for landscape
    
    # Construct set of destination points for A4 landscape size
    dst = np.array([
        [0, 0],
        [A4_WIDTH - 1, 0],
        [A4_WIDTH - 1, A4_HEIGHT - 1],
        [0, A4_HEIGHT - 1]], dtype=np.float32)
    
    # Compute the perspective transform matrix and apply it
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (A4_WIDTH, A4_HEIGHT))
    
    return warped

def detect_answers(section_img, questions=30, choices=4):
    # Convert to grayscale if not already
    if len(section_img.shape) == 3:
        gray = cv2.cvtColor(section_img, cv2.COLOR_BGR2GRAY)
    else:
        gray = section_img
    
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Get dimensions
    h, w = thresh.shape
    
    # Calculate bubble dimensions
    bubble_w = w // questions
    bubble_h = h // choices
    
    answers = {}
    for q in range(questions):
        marked = 0
        max_fill = 0
        for a in range(choices):
            # Calculate bubble coordinates
            x1 = q * bubble_w
            y1 = a * bubble_h
            x2 = (q + 1) * bubble_w
            y2 = (a + 1) * bubble_h
            
            # Extract bubble region
            bubble = thresh[y1:y2, x1:x2]
            
            # Count filled pixels
            fill = cv2.countNonZero(bubble)
            
            # Update if this is the most filled bubble
            if fill > max_fill and fill > (bubble_w * bubble_h * 0.3):  # 30% threshold
                max_fill = fill
                marked = a + 1
        
        answers[q + 1] = marked
    
    return answers

def process_answer_sheet(image_path):
    # Read and preprocess the image
    img = preprocess_image(image_path)
    
    # Find the page corners
    corners = find_page_corners(img)
    
    # Apply perspective transform to get a top-down view of the page
    warped = four_point_transform(img, corners)
    
    # Create a directory for sections if it doesn't exist
    sections_dir = "sections"
    if not os.path.exists(sections_dir):
        os.makedirs(sections_dir)
    
    # Define the exact coordinates for each section
    sections = [
        {"name": "section_1", "coords": (344, 608, 1861, 896)},
        {"name": "section_2", "coords": (356, 972, 1855, 1232)},
        {"name": "section_3", "coords": (341, 1311, 1855, 1562)},
        {"name": "section_4", "coords": (334, 1661, 1848, 1921)},
        {"name": "section_5", "coords": (337, 2017, 1848, 2278)},
        {"name": "section_6", "coords": (1904, 1318, 3403, 1568)},
        {"name": "section_7", "coords": (1889, 1664, 3427, 1931)},
        {"name": "section_8", "coords": (1901, 2022, 3393, 2282)}
    ]
    
    # Dictionary to store all answers
    all_answers = {}
    
    # Process each section
    for section in sections:
        x1, y1, x2, y2 = section["coords"]
        # Crop the section
        section_img = warped[y1:y2, x1:x2]
        
        # Save the section
        section_path = os.path.join(sections_dir, f"{section['name']}.jpg")
        cv2.imwrite(section_path, section_img, [cv2.IMWRITE_JPEG_QUALITY, 100])
        
        # Detect answers in this section
        section_answers = detect_answers(section_img)
        all_answers[section['name']] = section_answers
    
    # Save the full cropped page
    cv2.imwrite("cropped_page.jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, 100])
    
    return all_answers

# Example usage:
if __name__ == "__main__":
    result = process_answer_sheet(r"C:\Users\liorz\OneDrive\Desktop\PSY\answersheet.jpg")
    print("Page has been cropped and saved as 'cropped_page.jpg'")
    print("Sections have been saved in the 'sections' directory")
    print("\nDetected answers:")
    for section_name, answers in result.items():
        print(f"\n{section_name}:")
        for question, answer in answers.items():
            print(f"Question {question}: {answer}")
    