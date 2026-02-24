## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

from crewai.tools import BaseTool
from crewai_tools import SerperDevTool
from llama_index.readers.file import PDFReader
import logging

logger = logging.getLogger(__name__)

## Creating search tool
search_tool = SerperDevTool()

## Creating custom PDF reader tool using CrewAI's BaseTool
class ReadFinancialDocumentTool(BaseTool):
    name: str = "Read Financial Document"
    description: str = "Reads and extracts text content from a PDF financial document. Use this tool to access the uploaded financial document for analysis."
    
    def _run(self, file_path: str = None) -> str:
        """Reads and extracts text content from a PDF
        
        Args:
            file_path: Path to the PDF file (optional, will auto-detect from /app/data)
            
        Returns:
            str: Extracted text content from the PDF
        """
        try:
            # If no file_path provided, find the most recent PDF in /app/data
            if not file_path:
                import glob
                data_dir = "/app/data"
                pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
                if not pdf_files:
                    raise FileNotFoundError("No PDF files found in /app/data directory")
                # Use the most recently modified file
                file_path = max(pdf_files, key=os.path.getmtime)
                logger.info(f"Auto-detected PDF file: {file_path}")
            
            # Ensure file exists
            if not os.path.exists(file_path):
                # Try alternative paths
                alternatives = [
                    f"/app/data/{os.path.basename(file_path)}",
                    f"/data/{os.path.basename(file_path)}",
                    file_path
                ]
                found = False
                for alt_path in alternatives:
                    if os.path.exists(alt_path):
                        file_path = alt_path
                        found = True
                        break
                if not found:
                    raise FileNotFoundError(f"PDF file not found: {file_path} or alternatives")
            
            if not file_path.lower().endswith('.pdf'):
                raise ValueError(f"Expected PDF file: {file_path}")
            
            logger.info(f"Reading PDF from: {file_path}")
            pdf_reader = PDFReader()
            documents = pdf_reader.load_data(file_path)
            
            full_report = ""
            for doc in documents:
                content = doc.get_content() if hasattr(doc, 'get_content') else str(doc)
                content = ' '.join(content.split())
                full_report += content + "\n"
            
            if not full_report.strip():
                return "Warning: PDF appears to be empty"
            
            logger.info(f"Extracted {len(full_report)} characters from {file_path}")
            return full_report
            
        except Exception as e:
            logger.error(f"Error reading PDF: {str(e)}")
            raise


# Create instance
read_financial_document = ReadFinancialDocumentTool()

# Compatibility wrapper
class FinancialDocumentTool:
    """Compatibility wrapper"""
    read_data_tool = read_financial_document


## Creating Investment Analysis Tool
# Removed - not needed for agent tools


## Creating Risk Assessment Tool
# Removed - not needed for agent tools