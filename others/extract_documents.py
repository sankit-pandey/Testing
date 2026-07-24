import PyPDF2
from docx import Document
import os

def extract_pdf(pdf_path, output_path):
    """Extract text from PDF file"""
    print(f"Extracting PDF: {pdf_path}")
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = []
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text.append(f"\n{'='*80}\nPage {page_num}\n{'='*80}\n")
                text.append(page.extract_text())
            
            with open(output_path, 'w', encoding='utf-8') as output:
                output.write(''.join(text))
            print(f"✓ PDF extracted to: {output_path}")
            return True
    except Exception as e:
        print(f"✗ Error extracting PDF: {e}")
        return False

def extract_docx(docx_path, output_path):
    """Extract text from DOCX file"""
    print(f"Extracting DOCX: {docx_path}")
    try:
        doc = Document(docx_path)
        text = []
        
        for i, para in enumerate(doc.paragraphs, 1):
            if para.text.strip():
                text.append(para.text)
        
        with open(output_path, 'w', encoding='utf-8') as output:
            output.write('\n\n'.join(text))
        print(f"✓ DOCX extracted to: {output_path}")
        return True
    except Exception as e:
        print(f"✗ Error extracting DOCX: {e}")
        return False

if __name__ == "__main__":
    base_dir = r"C:\Projects\AI Localization"
    
    # Extract PDF
    pdf_file = os.path.join(base_dir, "Citiustech Localization Solution 1.pdf")
    pdf_output = os.path.join(base_dir, "Citiustech_Localization_Solution_1_extracted.txt")
    extract_pdf(pdf_file, pdf_output)
    
    # Extract DOCX
    docx_file = os.path.join(base_dir, "Knewron_Localization_Platform_Overview.docx")
    docx_output = os.path.join(base_dir, "Knewron_Localization_Platform_Overview_extracted.txt")
    extract_docx(docx_file, docx_output)
    
    print("\n" + "="*80)
    print("Extraction complete!")
    print("="*80)
