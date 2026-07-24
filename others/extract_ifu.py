import pdfplumber
import os

def extract_pdf_with_details(pdf_path, output_path):
    """Extract text from PDF with page details and metadata"""
    print(f"Extracting IFU PDF: {pdf_path}")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = []
            
            # PDF Metadata
            text.append("="*80)
            text.append("PDF METADATA")
            text.append("="*80)
            text.append(f"Total Pages: {len(pdf.pages)}")
            text.append(f"Metadata: {pdf.metadata}")
            text.append("\n")
            
            # Extract text from each page
            for page_num, page in enumerate(pdf.pages, 1):
                text.append(f"\n{'='*80}\nPage {page_num}\n{'='*80}\n")
                
                # Extract text
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
                
                # Count images on page
                images = page.images
                if images:
                    text.append(f"\n[Page {page_num} contains {len(images)} image(s)]")
                
                # Extract tables if any
                tables = page.extract_tables()
                if tables:
                    text.append(f"\n[Page {page_num} contains {len(tables)} table(s)]")
            
            with open(output_path, 'w', encoding='utf-8') as output:
                output.write('\n'.join(text))
            
            print(f"✓ IFU PDF extracted to: {output_path}")
            print(f"  Total pages: {len(pdf.pages)}")
            return True
    except Exception as e:
        print(f"✗ Error extracting PDF: {e}")
        return False

if __name__ == "__main__":
    base_dir = r"C:\Projects\AI Localization"
    
    # Extract IFU PDF
    pdf_file = os.path.join(base_dir, "DH_Diagnostic_Suite_IFU_US.pdf")
    pdf_output = os.path.join(base_dir, "DH_Diagnostic_Suite_IFU_US_extracted.txt")
    extract_pdf_with_details(pdf_file, pdf_output)
    
    print("\n" + "="*80)
    print("IFU Extraction complete!")
    print("="*80)
