import streamlit as st
import pandas as pd
import datetime
import os
import tempfile
import zipfile
from pathlib import Path
import qrcode
import random
from io import BytesIO
from utilities import (
    crop_face_for_profile, 
    create_circular_image, 
    add_circular_image_to_pdf, 
    replace_text_in_pdf, 
    normalize_text, 
    assemble_top_quarters
)

st.set_page_config(page_title="Aalto Foodsharing ID Generator", layout="wide")

st.title("🆔 Aalto Foodsharing ID Card Generator")

# Instructions section
st.header("📥 Get Data from SharePoint")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Download Registration Data")
    st.link_button(
        "📊 Open Registration Excel", 
        "https://aaltofi-my.sharepoint.com/:x:/r/personal/lukas_junghanns_aalto_fi/_layouts/15/Doc.aspx?sourcedoc=%7B5CC43194-128A-4DA0-994E-ACA720D67AEB%7D&file=Registration%20for%20Aalto%20Foodsharing%20%26%20Pickup%20introduction.xlsx",
        type="primary"
    )
    st.caption("Click above → File menu → Download → Upload below")

with col2:
    st.subheader("2. Download Face Photos")
    st.link_button(
        "📷 Open Photos Folder",
        "https://aaltofi-my.sharepoint.com/personal/lukas_junghanns_aalto_fi/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Flukas%5Fjunghanns%5Faalto%5Ffi%2FDocuments%2FApps%2FMicrosoft%20Forms%2FRegistration%20for%20Aalto%20Foodsharing%20%26%20Pickup%20introd%2FQuestion%201&FolderCTID=0x012000F2640C64C08C6F4FB7ED586C22DD6670&view=0",
        type="primary"
    )
    st.caption("Download all responses as ZIP → Upload below")

st.divider()

# File uploads
st.header("Upload Files")

col_csv, col_zip = st.columns(2)

with col_csv:
    csv_file = st.file_uploader("📄 Upload Registration Excel/CSV", type=['csv', 'xlsx'])

with col_zip:
    zip_file = st.file_uploader("📦 Upload Photos ZIP (with 'Question 1' folder)", type=['zip'])

def normalize_telegram_handle(handle):
    """Ensure Telegram handle starts with @ and return clean version"""
    if pd.isna(handle) or handle == "":
        return None
    handle = str(handle).strip()
    if not handle.startswith('@'):
        handle = '@' + handle
    return handle

def create_telegram_qr(telegram_handle):
    """Generate QR code for Telegram profile"""
    # Remove @ for URL
    username = telegram_handle.lstrip('@')
    url = f"https://t.me/{username}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes for Streamlit
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

if csv_file and zip_file:
    # Read CSV/Excel
    if csv_file.name.endswith('.csv'):
        registrations = pd.read_csv(csv_file)
    else:
        registrations = pd.read_excel(csv_file)
    
    # Column names
    date_column = 'For which introduction would you like to sign up? Please sign up at latest 2 days before the registered date. \n'
    photo_column = 'Please upload a picture with your face visible. It will be used for your personal Aalto Foodsharing ID only.'
    telegram_column = 'Telegram Tag (Note: Necessary because Telegram is our main communication channel)'
    
    # Check if columns exist
    if date_column not in registrations.columns:
        st.error(f"Column '{date_column}' not found in CSV. Available columns: {list(registrations.columns)}")
        st.stop()
    
    # Extract unique dates
    available_dates = registrations[date_column].dropna().unique().tolist()
    
    st.header("Select Introduction Date")
    selected_date = st.selectbox("Choose a date to generate IDs for:", available_dates)
    
    # Filter registrations
    filtered_registrations = registrations[registrations[date_column] == selected_date].copy()
    
    st.write(f"**{len(filtered_registrations)} people registered for {selected_date}**")
    
    # Extract filenames from photo URLs and normalize Telegram handles
    filtered_registrations['filename'] = filtered_registrations[photo_column].str.split('/').str[-1]
    filtered_registrations['telegram_normalized'] = filtered_registrations[telegram_column].apply(normalize_telegram_handle)
    
    st.dataframe(
        filtered_registrations[['Full Name', 'filename', 'telegram_normalized']],
        use_container_width=True
    )
    
    # Configuration
    st.header("Configuration")
    col1, col2 = st.columns(2)
    with col1:
        id_prefix = st.text_input("ID Prefix", value="2")
    with col2:
        bikelock_id = st.text_input("Bikelock ID", value="2")
    
    template_pdf_path = st.text_input("Path to ID template PDF", value="data/id_layout.pdf")
    
    # Generate button
    if st.button("🚀 Generate ID Cards", type="primary"):
        
        # Check if template exists
        if not Path(template_pdf_path).exists():
            st.error(f"Template PDF not found at: {template_pdf_path}")
            st.stop()
        
        # IMPORTANT: Keep EVERYTHING inside the same tempfile context
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            faces_dir = temp_path / "faces"
            output_dir = temp_path / "output"
            faces_dir.mkdir()
            output_dir.mkdir()
            
            with st.spinner("Extracting images from ZIP..."):
                # Extract ZIP file
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_path / "zip_contents")
                
                # Look for "Question 1" folder
                question_folder = temp_path / "zip_contents" / "Question 1"
                
                if not question_folder.exists():
                    # Try to find it recursively
                    found = False
                    for root, dirs, files in os.walk(temp_path / "zip_contents"):
                        if "Question 1" in dirs:
                            question_folder = Path(root) / "Question 1"
                            found = True
                            break
                    
                    if not found:
                        st.error("Could not find 'Question 1' folder in ZIP file")
                        all_dirs = [d for d in (temp_path / "zip_contents").rglob("*") if d.is_dir()]
                        st.write("All found directories:", [str(d) for d in all_dirs])
                        st.stop()
                
                # Copy images
                image_extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
                extracted_images = {}
                
                for file_path in question_folder.iterdir():
                    if file_path.suffix in image_extensions:
                        target_path = faces_dir / file_path.name
                        target_path.write_bytes(file_path.read_bytes())
                        extracted_images[file_path.name] = target_path
                
                st.write(f"**Extracted {len(extracted_images)} images**")
                
                # Show matching
                with st.expander("🔍 Filename Matching"):
                    for csv_name in filtered_registrations['filename'].tolist():
                        if csv_name in extracted_images:
                            st.write(f"✅ {csv_name}")
                        else:
                            st.write(f"❌ {csv_name}")
            
            with st.spinner("Generating ID cards..."):
                # Process each person
                progress_bar = st.progress(0)
                status_text = st.empty()
                total = len(filtered_registrations)
                success_count = 0
                errors = []
                successful_people = []  # Track successful generations with their data
                codes = st.secrets["CODES"]
                codes = codes.split(", ")
                random_selection = random.sample(codes, len(filtered_registrations))
                for idx, (index, row) in enumerate(filtered_registrations.iterrows()):
                    try:
                        name = normalize_text(row['Full Name'])
                        status_text.text(f"Processing {idx+1}/{total}: {name}")
                        
                        expected_filename = row['filename']
                        
                        if expected_filename not in extracted_images:
                            errors.append(f"{name}: Image not found (expected: {expected_filename})")
                            continue
                        
                        input_path = extracted_images[expected_filename]
                        temp_pdf = output_dir / "temp.pdf"
                        
                        # Step 1: Crop face
                        face_img = crop_face_for_profile(
                            str(input_path), 
                            padding=0.5, 
                            target_size=(500, 500)
                        )
                        
                        if face_img is None:
                            errors.append(f"{name}: No face detected in image")
                            continue
                        
                        # Step 2: Create circular image
                        circular_img = create_circular_image(face_img)
                        
                        # Step 3: Add to PDF template
                        add_circular_image_to_pdf(
                            circular_img, 
                            str(temp_pdf), 
                            x_pos=210, 
                            y_pos=703.8, 
                            diameter=66, 
                            page_size='letter', 
                            template_pdf=template_pdf_path
                        )
                        
                        # Step 4: Replace text
                        today = datetime.datetime.now()
                        issued_date = f'{today.day}.{today.month}.{today.year}'
                        
                        parameter = {
                            'FS-ID': [8, f'#{random_selection}'], 
                            'ACTIVE-DATE': [11, issued_date], 
                            'ISSED-DATE': [11, issued_date], 
                            'NAME-TAG': [12, name]
                        }
                        
                        final_pdf = output_dir / f"{name.replace(' ', '_')}_id.pdf"
                        replace_text_in_pdf(str(temp_pdf), str(final_pdf), parameter)
                        
                        # Clean up temp file
                        temp_pdf.unlink(missing_ok=True)
                        success_count += 1
                        
                        # Track successful generation
                        successful_people.append({
                            'name': row['Full Name'],
                            'telegram': row['telegram_normalized']
                        })
                        
                    except Exception as e:
                        errors.append(f"{name}: {str(e)}")
                    
                    progress_bar.progress((idx + 1) / total)
                
                # Show errors if any
                if errors:
                    with st.expander("⚠️ Errors and Warnings"):
                        for error in errors:
                            st.write(f"• {error}")
                
                # Only assemble if we have successful outputs
                if success_count > 0:
                    status_text.text("Assembling final PDF...")
                    
                    # Assemble into final PDF
                    final_assembled = temp_path / "assembled_ids.pdf"
                    assemble_top_quarters(str(output_dir), str(final_assembled))
                    
                    # Provide download
                    with open(final_assembled, 'rb') as f:
                        st.download_button(
                            label="📥 Download Assembled ID Cards",
                            data=f.read(),
                            file_name=f"foodsharing_ids_{selected_date.replace(' ', '_').replace('/', '-')}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                    
                    st.success(f"✅ Successfully generated {success_count}/{total} ID cards!")
                    
                    # Show Telegram contact info
                    st.divider()
                    st.header("📱 Contact Participants via Telegram")
                    
                    st.write("Use these links and QR codes to easily contact participants:")
                    
                    for person in successful_people:
                        name = person['name']
                        telegram = person['telegram']
                        
                        with st.expander(f"💬 {name}"):
                            if telegram:
                                username = telegram.lstrip('@')
                                telegram_url = f"https://t.me/{username}"
                                
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.markdown(f"**Telegram:** [{telegram}]({telegram_url})")
                                    
                                    # Message template
                                    message = f"Hey {name}, nice that you signed up for the introduction pick up at: {selected_date}, see you at the Väre Fridge!"
                                    st.text_area(
                                        "Message to copy:",
                                        message,
                                        height=100,
                                        key=f"msg_{username}"
                                    )
                                
                                with col2:
                                    # Generate and display QR code
                                    qr_img = create_telegram_qr(telegram)
                                    st.image(qr_img, caption=f"Scan to message {telegram}", width=200)
                            else:
                                st.warning("⚠️ No Telegram handle provided")
                    
                
                    
                else:
                    st.error(f"❌ No ID cards were generated successfully. Check the errors above.")

elif csv_file and not zip_file:
    st.info("👆 Please also upload the ZIP file with photos")
elif zip_file and not csv_file:
    st.info("👆 Please also upload the registration CSV/Excel file")
else:
    st.info("👆 Upload both files to get started")
