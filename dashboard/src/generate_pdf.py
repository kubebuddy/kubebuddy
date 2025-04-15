from django.http import HttpResponse
from xhtml2pdf import pisa
import io

def generate_pdf(html, result):
    # Define page options for A4 portrait - size is in mm
    pdf_options = {
        'page-size': 'A4',
        'orientation': 'portrait',
        'margin-top': '15mm',
        'margin-right': '15mm',
        'margin-bottom': '15mm',
        'margin-left': '15mm',
        'encoding': 'UTF-8',
    }
    
    # Add necessary CSS for PDF compatibility
    pdf_css = """
    <style>
        body {
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
      font-size: 12px;
    }
    
    .heading{
          font-size: 48px;
          color: navy;
          text-align: center;
    }

    .cover-page {
      width: 100%;
      padding: 20px 0;
      margin: 0;
      display: block;
      page-break-after: always;
    }
    
    .logo {
      display: block;
      width: 250px;
      height: auto;
      margin: 20px auto;
    }
    
    .title-container {
      background: lightblue;
      width: 80%;
      margin: 20px auto;
      padding: 20px;
      text-align: center;
    }
    
    .title-text {
      color: white;
      font-size: 24px;
      text-align: center;
      margin: 0;
    }
    
    .slogan {
      font-size: 18px;
      color: midnightblue;
      text-align: center;
      margin: 15px 0;
    }
    
    .footer-info {
      margin-top: 50px;
      text-align: right;
      padding-right: 50px;
    }
    
    .copyright {
      font-size: 10px;
      font-style: italic;
      text-align: center;
      margin-top: 30px;
    }
    
    .content-page {
      width: 100%;
      margin: 0;
      padding: 10px 0;
      page-break-after: always;
    }
    
    .section-title {
      color: navy;
      text-align: center;
      font-size: 18px;
      border-bottom: 2px solid darkblue;
      padding-bottom: 5px;
      margin-top: 20px;
    }
    
    .subsection-title {
      color: navy;
      text-align: center;
      font-size: 16px;
      margin-top: 15px;
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0;
      font-size: 10px;
    }
    
    th, td {
      border: 1px solid lightgrey;
      padding: 4px;
      text-align: center;
      word-wrap: break-word;
    }
    
    .no-data {
      text-align: center;
    }
    
    .status-ready {
      color: green;
    }
    
    .status-notready {
      color: red;
    }
    
    .status-unknown {
      color: orange;
    }
    
    .host-list {
      list-style-type: none;
      padding: 0;
      margin: 0;
    }
    
    /* Add page break controls */
    .page-break {
      page-break-after: always;
    }
    
    /* Make sure tables don't overflow */
    table {
      table-layout: fixed;
    }
    
    /* Ensure content fits within PDF */
    @page {
      size: a4 portrait;
      margin: 15mm;
    }
    </style>
    """
    
    # Insert the additional CSS into the HTML
    modified_html = html
    if '</head>' in html:
        modified_html = html.replace('</head>', f'{pdf_css}</head>')
    
    # Handle different types of result objects
    buffer = None
    
    try:
        # If result is an HttpResponse
        if isinstance(result, HttpResponse):
            buffer = io.BytesIO()
            # Convert HTML to PDF
            pisa_status = pisa.CreatePDF(
                modified_html,
                dest=buffer,
                options=pdf_options
            )
            # Write the PDF to the HttpResponse
            if pisa_status.err == 0:
                result.write(buffer.getvalue())
                buffer.close()
            return pisa_status.err == 0
        
        # If result is a file path string
        elif isinstance(result, (str, bytes)) or hasattr(result, '__fspath__'):
            with open(result, "wb") as output_file:
                pisa_status = pisa.CreatePDF(
                    modified_html,
                    dest=output_file,
                    options=pdf_options
                )
            return pisa_status.err == 0
        
        # If result is a file-like object
        else:
            pisa_status = pisa.CreatePDF(
                modified_html,
                dest=result,
                options=pdf_options
            )
            return pisa_status.err == 0
            
    except Exception as e:
        print(f"Error generating PDF: {e}")
        if buffer:
            buffer.close()
        return False