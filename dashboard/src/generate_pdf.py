from django.http import HttpResponse
from playwright.sync_api import sync_playwright
import tempfile
import os

def generate_pdf(html, result):
    try:
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as temp_file:
            temp_file.write(html)
            temp_file_path = temp_file.name

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                # Load the HTML content
                page.goto(f'file://{temp_file_path}')
                
                # Wait for content to load
                page.wait_for_load_state('networkidle')
                
                # Generate PDF
                pdf_content = page.pdf(
                    format='A4',
                    print_background=True,
                    margin={
                        'top': '15mm',
                        'right': '15mm',
                        'bottom': '15mm',
                        'left': '15mm'
                    }
                )
                
                # Write the PDF content to the appropriate output
                if isinstance(result, HttpResponse):
                    result.write(pdf_content)
                else:
                    with open(result, 'wb') as f:
                        f.write(pdf_content)
                
                browser.close()
                return True
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass
            
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return False