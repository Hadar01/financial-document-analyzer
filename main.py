from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import os
import uuid
import asyncio
import logging
import time
from pathlib import Path
from datetime import datetime

from crewai import Crew, Process
from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from task import (
    analyze_financial_document,
    investment_analysis,
    risk_assessment,
    verification
)
from db_models import init_db, engine, Analysis, AnalysisResult
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial Document Analyzer",
    description="Comprehensive financial document analysis using AI agents",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup"""
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # Don't crash if db init fails - it might already be initialized
        pass

# Ensure data directory exists
DATA_DIR = Path("data")
OUTPUTS_DIR = Path("outputs")
DATA_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Database session
SessionLocal = sessionmaker(bind=engine)

def get_db_session():
    """Get a database session"""
    return SessionLocal()


def validate_pdf_file(file_path: str) -> bool:
    """Validate if the file is a proper PDF"""
    try:
        if not os.path.exists(file_path):
            return False
        
        # Check file extension
        if not file_path.lower().endswith('.pdf'):
            return False
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"File size {file_size} exceeds maximum allowed {MAX_FILE_SIZE}")
            return False
        
        # Check for valid PDF header
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                logger.warning(f"File does not have valid PDF header")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating PDF file: {str(e)}")
        return False


def extract_pdf_text(file_path: str) -> str:
    """Extract text content from a PDF file"""
    from llama_index.readers.file import PDFReader
    pdf_reader = PDFReader()
    documents = pdf_reader.load_data(file_path)
    full_text = ""
    for doc in documents:
        content = doc.get_content() if hasattr(doc, 'get_content') else str(doc)
        content = ' '.join(content.split())
        full_text += content + "\n"
    return full_text.strip()


def run_financial_analysis_crew(query: str, file_path: str) -> dict:
    """Execute the complete financial analysis crew with all agents and tasks"""
    try:
        logger.info(f"Starting financial analysis crew for query: {query}")
        
        # Verify file exists and is valid PDF
        if not validate_pdf_file(file_path):
            raise ValueError("Invalid or missing PDF file")
        
        # PRE-READ the PDF content so agents get it directly
        logger.info(f"Extracting text from PDF: {file_path}")
        document_content = extract_pdf_text(file_path)
        if not document_content:
            raise ValueError("Could not extract text from PDF")
        logger.info(f"Extracted {len(document_content)} characters from PDF")
        
        # Truncate if too long (keep first 15000 chars to fit in context)
        max_chars = 15000
        if len(document_content) > max_chars:
            document_content = document_content[:max_chars] + "\n\n[Document truncated due to length...]"
        
        # Build context with document content embedded
        crew_input = {
            'query': query,
            'document_content': document_content
        }
        
        # Create crew with proper sequencing
        # First: Verify the document
        verification_crew = Crew(
            agents=[verifier],
            tasks=[verification],
            process=Process.sequential,
            verbose=True
        )
        
        logger.info("Running document verification...")
        verification_result = verification_crew.kickoff(crew_input)
        
        # Second: Analyze financial document
        analysis_crew = Crew(
            agents=[financial_analyst],
            tasks=[analyze_financial_document],
            process=Process.sequential,
            verbose=True
        )
        
        logger.info("Running financial analysis...")
        analysis_result = analysis_crew.kickoff(crew_input)
        
        # Third: Investment analysis
        investment_crew = Crew(
            agents=[investment_advisor],
            tasks=[investment_analysis],
            process=Process.sequential,
            verbose=True
        )
        
        logger.info("Running investment analysis...")
        investment_result = investment_crew.kickoff(crew_input)
        
        # Fourth: Risk assessment
        risk_crew = Crew(
            agents=[risk_assessor],
            tasks=[risk_assessment],
            process=Process.sequential,
            verbose=True
        )
        
        logger.info("Running risk assessment...")
        risk_result = risk_crew.kickoff(crew_input)
        
        return {
            'verification': str(verification_result),
            'analysis': str(analysis_result),
            'investment': str(investment_result),
            'risk': str(risk_result)
        }
        
    except Exception as e:
        logger.error(f"Error in financial analysis crew: {str(e)}")
        raise


@app.get("/")
async def root():
    """Serve the web UI"""
    index_path = Path("index.html")
    if index_path.exists():
        return FileResponse(index_path)
    # Fallback if HTML file not found
    return {
        "message": "Financial Document Analyzer API is running",
        "version": "1.0.0",
        "ui": "Visit http://localhost:8000 in your browser",
        "endpoints": {
            "analyze": "/analyze",
            "health": "/health",
            "api": "/api"
        }
    }


@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "message": "Financial Document Analyzer API is running",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "/analyze",
            "health": "/health",
            "ui": "/"
        }
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "Financial Document Analyzer",
        "data_directory": str(DATA_DIR.absolute()),
        "outputs_directory": str(OUTPUTS_DIR.absolute())
    }


@app.post("/analyze")
async def analyze_financial_document_endpoint(
    file: UploadFile = File(...),
    query: str = Form(default="Provide comprehensive financial analysis of the submitted document")
):
    """
    Analyze a financial document and provide comprehensive investment recommendations.
    
    Args:
        file: PDF file to analyze
        query: Specific analysis query or instruction
        
    Returns:
        Analysis results including verification, financial analysis, investment recommendations, and risk assessment
    """
    
    file_id = str(uuid.uuid4())
    file_path = DATA_DIR / f"financial_document_{file_id}.pdf"
    output_path = OUTPUTS_DIR / f"analysis_{file_id}.json"
    
    try:
        # Validate query
        if not query or query.strip() == "":
            query = "Provide comprehensive financial analysis of the submitted document"
        
        query = query.strip()
        
        # Validate file
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Save uploaded file
        logger.info(f"Saving uploaded file: {file.filename}")
        os.makedirs(DATA_DIR, exist_ok=True)
        
        content = await file.read()
        
        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        # Validate PDF header
        if not content.startswith(b'%PDF'):
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is not a valid PDF"
            )
        
        # Write file
        with open(str(file_path), "wb") as f:
            f.write(content)
        
        # Run analysis
        logger.info(f"Starting analysis for file: {file.filename}")
        results = run_financial_analysis_crew(query, str(file_path))
        
        # Save results
        import json
        with open(str(output_path), "w") as f:
            json.dump({
                'file_id': file_id,
                'filename': file.filename,
                'query': query,
                'results': results
            }, f, indent=2)
        
        logger.info(f"Analysis completed successfully for file: {file.filename}")
        
        # Save to database
        try:
            db = get_db_session()
            
            # Create Analysis record
            analysis_record = Analysis(
                file_id=file_id,
                filename=file.filename,
                query=query,
                status="completed",
                completed_at=datetime.utcnow()
            )
            db.add(analysis_record)
            db.flush()  # Get the id without committing yet
            
            # Create AnalysisResult record
            result_record = AnalysisResult(
                analysis_id=analysis_record.id,
                verification=results.get('verification', ''),
                financial_analysis=results.get('analysis', ''),
                investment_recommendations=results.get('investment', ''),
                risk_assessment=results.get('risk', ''),
                result_metadata={
                    'filename': file.filename,
                    'output_file': str(output_path)
                },
                processing_time=0
            )
            db.add(result_record)
            db.commit()
            
            logger.info(f"Results saved to database for file_id: {file_id}")
            
        except Exception as db_error:
            logger.error(f"Error saving to database: {str(db_error)}")
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()
        
        return {
            "status": "success",
            "file_id": file_id,
            "filename": file.filename,
            "query": query,
            "analysis_results": results,
            "output_file": str(output_path)
        }
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        raise HTTPException(status_code=404, detail=f"File processing error: {str(e)}")
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing financial document: {str(e)}"
        )
    
    finally:
        # Clean up uploaded file after processing
        if os.path.exists(str(file_path)):
            try:
                os.remove(str(file_path))
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {file_path}: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )