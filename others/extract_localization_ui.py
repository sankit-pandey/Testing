import PyPDF2
import os

def extract_pdf(pdf_path, output_path):
    """Extract text from PDF file"""
    print(f"Extracting PDF: {pdf_path}")
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"Total pages: {len(pdf_reader.pages)}")
            text = []
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text.append(f"\n{'='*80}\nPage {page_num}\n{'='*80}\n")
                page_text = page.extract_text()
                text.append(page_text)
                print(f"Extracted page {page_num}/{len(pdf_reader.pages)}")
            
            with open(output_path, 'w', encoding='utf-8') as output:
                output.write(''.join(text))
            print(f"✓ PDF extracted to: {output_path}")
            return True
    except Exception as e:
        print(f"✗ Error extracting PDF: {e}")
        return False

if __name__ == "__main__":
    pdf_file = r"C:\Projects\AI Localization\Localization UI.pdf"
    output_file = r"C:\Projects\AI Localization\Localization_UI_extracted.txt"
    extract_pdf(pdf_file, output_file)
