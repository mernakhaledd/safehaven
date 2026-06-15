
import PyPDF2
import sys

def extract_text_from_pdf(pdf_path, start_page, end_page):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            
            print(f"Total pages: {num_pages}")
            
            for i in range(start_page - 1, end_page):
                if i < num_pages:
                    page = reader.pages[i]
                    text = page.extract_text()
                    print(f"\n--- Slide {i + 1} ---\n")
                    print(text)
                else:
                    print(f"\n--- Slide {i + 1} (Not found) ---\n")
                    
    except ImportError:
        print("Error: PyPDF2 module not found. Please install it using 'pip install PyPDF2(or pypdf)'")
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    # PDF path provided by user
    pdf_path = r"C:\Users\DELL\Downloads\SafeHaven  (1).pdf"
    # Extract slides 11 to 14
    extract_text_from_pdf(pdf_path, 11, 14)
