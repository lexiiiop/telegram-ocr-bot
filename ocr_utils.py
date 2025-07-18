from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from autocorrect import Speller
import os
from config import GEMINI_API_KEY

# List of at least 20 supported Tesseract language codes
SUPPORTED_LANGS = [
    "eng", "hin", "spa", "fra", "deu", "ita", "por", "rus", "jpn", "chi_sim",
    "ara", "tur", "nld", "pol", "ces", "ell", "kor", "ukr", "ron", "swe"
]

spell = Speller(lang='en')

def preprocess_image(image_path):
    img = Image.open(image_path).convert("L")  # grayscale
    img = img.point(lambda x: 0 if x < 140 else 255)  # binarize
    img = img.filter(ImageFilter.MedianFilter())  # denoise
    return img

def extract_text(file_path: str, lang=None) -> str:
    # If no lang specified, use all supported for auto-detection
    if not lang:
        lang = "+".join(SUPPORTED_LANGS)
    try:
        img = preprocess_image(file_path)
        text = pytesseract.image_to_string(img, lang=lang)
        corrected_text = spell(text)
        return corrected_text.strip() or "No text found."
    except Exception as e:
        return f"OCR error: {str(e)}"

# Gemini OCR integration
def gemini_ocr(file_path: str) -> str:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        img = Image.open(file_path)
        response = model.generate_content([
            "Extract all text from this image. Return only the text, no commentary.",
            img
        ])
        return response.text.strip() or "No text found."
    except Exception as e:
        return f"Gemini OCR error: {str(e)}" 