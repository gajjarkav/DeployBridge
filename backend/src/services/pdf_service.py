import io
import markdown
from xhtml2pdf import pisa
from ..core.logger import logger

class PDFService:
    @staticmethod
    def generate_pdf_from_markdown(md_text: str, repo_name: str) -> bytes:
        """
        Convert markdown report to PDF bytes.
        Uses markdown to convert to HTML, then xhtml2pdf to generate PDF.
        """
        try:
            html_content = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
            
            # Add basic styling to make it look professional
            styled_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Helvetica, sans-serif; font-size: 12px; color: #333; }}
                    h1 {{ color: #000; font-size: 24px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                    h2 {{ color: #222; font-size: 18px; margin-top: 20px; }}
                    h3 {{ color: #444; font-size: 14px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; }}
                    th {{ background-color: #f5f5f5; font-weight: bold; }}
                    code {{ font-family: Courier, monospace; background-color: #f9f9f9; padding: 2px 4px; }}
                    pre {{ background-color: #f5f5f5; padding: 10px; border: 1px solid #ddd; }}
                </style>
            </head>
            <body>
                <h1>DeployBridge AI Analysis: {repo_name}</h1>
                {html_content}
            </body>
            </html>
            """
            
            result = io.BytesIO()
            pisa_status = pisa.CreatePDF(io.StringIO(styled_html), dest=result)
            
            if pisa_status.err:
                logger.error(f"Error generating PDF: {pisa_status.err}")
                raise Exception("Failed to generate PDF")
                
            return result.getvalue()
            
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            raise
