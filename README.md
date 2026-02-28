# 🆔 Aalto Foodsharing ID Generator

An automated tool designed for **Aalto Foodsharing** organizers to quickly generate member ID cards from Microsoft Form registrations. This app handles face detection, image cropping, PDF text replacement, and even generates Telegram contact shortcuts for new members.

## ✨ Features

* **Data Integration:** Directly processes Excel/CSV exports from SharePoint.
* **Automatic Face Cropping:** Uses computer vision to detect faces and crop them into circular profile pictures.
* **PDF Templating:** Injects member names, unique ID codes, and dates into a standardized PDF layout.
* **Bulk Assembly:** Merges individual IDs into a single print-ready PDF (4 IDs per page).
* **Telegram Shortcuts:** Generates QR codes and message templates to contact participants instantly via Telegram.

---

## 🛠️ Installation & Setup

### 1. Requirements

Ensure your `requirements.txt` includes the following (and **excludes** standard libraries like `random` or `os`):

```text
streamlit
pandas
openpyxl
opencv-python-headless
Pillow
reportlab
PyMuPDF
PyPDF2
qrcode

```

### 2. File Structure

The app expects the following files to be present in your repository:

```text
├── app.py                # Main Streamlit code
├── utilities.py          # Image & PDF processing functions
├── data/
│   └── id_layout.pdf     # The base PDF template
└── requirements.txt

```

### 3. Streamlit Secrets

This app uses a secret key to pull a list of available ID codes. In your Streamlit Cloud dashboard, go to **Settings > Secrets** and add:

```toml
CODES = "1001, 1002, 1003, 1004, 1005" # Add your list of unique IDs here

```

---

## 🚀 How to Use

1. **Export Data:** * Download the Registration Excel from SharePoint as a **CSV (UTF-8)**.
* Download the "Photos" folder from Microsoft Forms as a **ZIP file** (Do not unzip it).


2. **Upload:** Drop both files into the sidebar/upload area.
3. **Filter:** Select the specific "Introduction Date" you want to generate cards for.
4. **Generate:** Click `🚀 Generate ID Cards`. The app will match the names in the CSV to the filenames in the ZIP.
5. **Download:** Once processing is complete, download the `assembled_ids.pdf` and start printing!

---

## 🔧 Technical Workflow

1. **Normalization:** Cleans Telegram handles and participant names for consistent formatting.
2. **Face Detection:** Uses `opencv-python-headless` to locate faces in uploaded photos to ensure the ID looks professional.
3. **PDF Manipulation:** Uses `PyMuPDF` and `PyPDF2` to overlay images and modify text layers on the template without losing PDF quality.
4. **Temporary Storage:** Uses `tempfile` to ensure user data is wiped from the server as soon as the session ends, maintaining privacy.

---

## 👥 Contributors

* Developed for the **Aalto Foodsharing** community.
* Maintainer: [Your Name/GitHub Profile]

---
