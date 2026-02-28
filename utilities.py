import cv2
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader
import fitz
import os

def crop_face_for_profile(image_path, output_path=None, padding=0.3, target_size=(400, 400)):
    """
    Detect and crop face from an image for use as a profile picture.
    
    Args:
        image_path: Path to input image
        output_path: Path to save cropped image (optional)
        padding: Extra space around face (0.3 = 30% padding)
        target_size: Output image size as (width, height)
    
    Returns:
        Cropped face image or None if no face detected
    """
    # Load the image
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"Error: Could not load image from {image_path}")
        return None
    
    # Convert to grayscale for face detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Load the pre-trained face detection model
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    if len(faces) == 0:
        print("No faces detected in the image")
        return None
    
    # Use the largest face detected
    largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
    x, y, w, h = largest_face
    
    # Calculate padding
    pad_w = int(w * padding)
    pad_h = int(h * padding)
    
    # Calculate crop coordinates with padding
    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(img.shape[1], x + w + pad_w)
    y2 = min(img.shape[0], y + h + pad_h)
    
    # Crop the face region
    face_crop = img[y1:y2, x1:x2]
    
    # Resize to target size
    face_resized = cv2.resize(face_crop, target_size, interpolation=cv2.INTER_AREA)
    
    # Save if output path provided
    if output_path:
        cv2.imwrite(str(output_path), face_resized)
        print(f"Profile picture saved to: {output_path}")
    
    return face_resized

def create_circular_image(image_array, output_path=None):
    """
    Convert image to circular shape with transparent background.
    
    Args:
        image_array: Image as numpy array (from OpenCV)
        output_path: Path to save circular image (optional)
    
    Returns:
        PIL Image with circular mask and transparent background
    """
    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
    
    # Convert to PIL Image
    pil_img = Image.fromarray(img_rgb)
    
    # Create a new image with transparency
    size = pil_img.size
    circle_img = Image.new('RGBA', size, (255, 255, 255, 0))
    
    # Create circular mask
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    
    # Apply mask to make it circular
    circle_img.paste(pil_img.convert('RGBA'), (0, 0), mask)
    
    if output_path:
        circle_img.save(output_path, 'PNG')
    
    return circle_img

def add_circular_image_to_pdf(circular_image, output_pdf, x_pos, y_pos, 
                               diameter=100, page_size='letter', 
                               template_pdf=None):
    """
    Add circular profile image to a PDF at specified position.
    
    Args:
        circular_image: PIL Image object with transparency
        output_pdf: Path for output PDF
        x_pos: X position in points (from left)
        y_pos: Y position in points (from bottom)
        diameter: Diameter of circle in points
        page_size: 'letter' or 'A4' or tuple (width, height)
        template_pdf: Path to existing PDF to overlay image on (optional)
    """
    # Set page size
    if page_size == 'letter':
        psize = letter
    elif page_size == 'A4':
        psize = A4
    else:
        psize = page_size
    
    # Create canvas
    c = canvas.Canvas(output_pdf, pagesize=psize)
    
    # If template PDF provided, handle it
    if template_pdf:
        from PyPDF2 import PdfReader, PdfWriter
        import io
        
        # Create temporary PDF with just the image
        temp_buffer = io.BytesIO()
        temp_canvas = canvas.Canvas(temp_buffer, pagesize=psize)
        temp_canvas.drawImage(ImageReader(circular_image), 
                            x_pos, y_pos, 
                            width=diameter, height=diameter, 
                            mask='auto')
        temp_canvas.save()
        
        # Merge with template
        temp_buffer.seek(0)
        template_reader = PdfReader(template_pdf)
        overlay_reader = PdfReader(temp_buffer)
        writer = PdfWriter()
        
        # Merge first page
        page = template_reader.pages[0]
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)
        
        # Add remaining pages from template
        for i in range(1, len(template_reader.pages)):
            writer.add_page(template_reader.pages[i])
        
        # Write final PDF
        with open(output_pdf, 'wb') as f:
            writer.write(f)
        
        return
    
    # Draw circular image on new PDF
    c.drawImage(ImageReader(circular_image), 
                x_pos, y_pos, 
                width=diameter, height=diameter, 
                mask='auto')
    
    c.save()

def normalize_text(text):
    """Remove diacritics for PDF compatibility"""
    replacements = {
        'š': 's', 'Š': 'S',
        'ć': 'c', 'Ć': 'C',
        'č': 'c', 'Č': 'C',
        'ž': 'z', 'Ž': 'Z',
        'đ': 'd', 'Đ': 'D',
    }
    for original, replacement in replacements.items():
        text = text.replace(original, replacement)
    return text

def replace_text_in_pdf(input_pdf_path, output_pdf_path, parameter):
    doc = fitz.open(input_pdf_path)
    
    for page in doc:
        for placeholder in list(parameter.keys()):
            text_instances = page.search_for(placeholder)
            
            for inst in text_instances:
                rect = fitz.Rect(inst[0], inst[1], inst[2], inst[3])
                white = (0.9882352941176471, 0.9764705882352941, 0.9490196078431372)
                page.draw_rect(rect, color=white, fill=white)
                page.insert_text(rect.bl, parameter.get(placeholder)[1], 
                               fontsize=parameter.get(placeholder)[0], 
                               fontname='Courier-Bold', fill_opacity=1.75)
    
    doc.save(output_pdf_path)
    doc.close()  # EXPLICITLY CLOSE

def assemble_top_quarters(input_folder="data/new", output_filename="assembled_quarters.pdf", batch_size=4):
    """
    Takes the top 25% of the first page of each PDF in a folder.
    Assembles them vertically onto new pages (4 per page).
    """
    # Ensure the folder exists
    if not os.path.exists(input_folder):
        print(f"Error: Folder '{input_folder}' does not exist.")
        return

    # Get all PDF files and sort them
    files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')])
    
    if not files:
        print(f"No PDF files found in {input_folder}")
        return

    # Create a new blank PDF document for our final output
    doc_out = fitz.open()

    # Process files in chunks of 4
    for i in range(0, len(files), batch_size):
        current_batch = files[i : i + batch_size]
        
        # Open the first PDF in this batch to get standard page dimensions (width & height)
        first_pdf = fitz.open(os.path.join(input_folder, current_batch[0]))
        standard_width = first_pdf[0].rect.width
        standard_height = first_pdf[0].rect.height
        first_pdf.close()
        
        # Create a blank page in our output document using those standard dimensions
        page_out = doc_out.new_page(width=standard_width, height=standard_height)
        
        # Now, paste the top 25% of each PDF into its respective slot
        for j, filename in enumerate(current_batch):
            pdf_path = os.path.join(input_folder, filename)
            doc_in = fitz.open(pdf_path)
            
            in_width = doc_in[0].rect.width
            in_height = doc_in[0].rect.height
            
            # 1. Define what to CUT (The top 25%)
            # PyMuPDF uses (x0, y0, x1, y1) where (0,0) is the top-left corner
            clip_rect = fitz.Rect(0, 0, in_width, in_height * 0.25)
            
            # 2. Define where to PASTE (Shift down by 25% for each subsequent file)
            # Slot 0 is top, Slot 1 is second quarter, etc.
            y_offset = j * (standard_height * 0.25)
            target_rect = fitz.Rect(0, y_offset, standard_width, y_offset + (standard_height * 0.25))
            
            # Stamp the clipped rectangle onto our new page
            page_out.show_pdf_page(target_rect, doc_in, 0, clip=clip_rect)
            doc_in.close()
            
    # Save the final merged document
    doc_out.save(output_filename)
    doc_out.close()
    
    # Calculate expected pages
    expected_pages = (len(files) + batch_size - 1) // batch_size
    print(f"Success! Merged {len(files)} files into 1 PDF with {expected_pages} page(s).")
    print(f"Saved as: {output_filename}")
