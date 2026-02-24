"""
Celery tasks for asynchronous financial document analysis
Handles document verification, analysis, and result storage
"""

import logging
import os
import time
from pathlib import Path
from datetime import datetime
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from celery_app import app
from main import validate_pdf_file, run_financial_analysis_crew
from db_models import (
    get_db,
    update_analysis_status,
    create_analysis_result,
    log_audit,
    Analysis
)

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=900,  # 15 minutes hard limit
    track_started=True,
    name='tasks.analyze_financial_document_task'
)
def analyze_financial_document_task(
    self,
    file_path: str,
    query: str,
    file_id: str,
    filename: str,
    analysis_id: int = None,
    user_id: int = None
) -> dict:
    """
    Celery task to analyze financial document
    
    Args:
        file_path: Path to the PDF file
        query: Analysis query
        file_id: Unique file identifier
        filename: Original filename
        analysis_id: Database analysis record ID
        user_id: User ID for audit logging
        
    Returns:
        Dictionary with analysis results
        
    Raises:
        SoftTimeLimitExceeded: If task exceeds time limit
    """
    start_time = time.time()
    db = None
    
    try:
        db = next(get_db())
        
        logger.info(f"Starting analysis task {self.request.id} for {filename}")
        
        # Update status to processing
        if analysis_id:
            update_analysis_status(db, analysis_id, "processing", task_id=self.request.id)
        
        # Validate file
        if not validate_pdf_file(file_path):
            raise ValueError("Invalid PDF file")
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Verifying document...',
                'percentage': 10
            }
        )
        
        # Run analysis crew
        logger.info("Running financial analysis crew...")
        results = run_financial_analysis_crew(query, file_path)
        
        # Calculate processing time
        processing_time = int(time.time() - start_time)
        
        # Store results in database
        if analysis_id:
            create_analysis_result(
                db,
                analysis_id=analysis_id,
                verification=results.get('verification', ''),
                financial_analysis=results.get('analysis', ''),
                investment_recommendations=results.get('investment', ''),
                risk_assessment=results.get('risk', ''),
                metadata={
                    'task_id': self.request.id,
                    'file_id': file_id,
                    'completion_time': datetime.utcnow().isoformat()
                },
                processing_time=processing_time
            )
            
            # Update analysis status to completed
            update_analysis_status(db, analysis_id, "completed")
            
            # Audit log
            log_audit(
                db,
                action='analyze_document',
                resource_type='analysis',
                resource_id=analysis_id,
                status='success',
                user_id=user_id,
                details=f'Analysis completed in {processing_time}s'
            )
        
        # Clean up uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {str(e)}")
        
        logger.info(f"Analysis task {self.request.id} completed in {processing_time}s")
        
        return {
            'status': 'success',
            'file_id': file_id,
            'filename': filename,
            'task_id': self.request.id,
            'processing_time': processing_time,
            'results': results
        }
        
    except SoftTimeLimitExceeded as e:
        logger.error(f"Task {self.request.id} exceeded time limit")
        if analysis_id and db:
            update_analysis_status(db, analysis_id, "failed", error_message="Task timeout")
            log_audit(db, 'analyze_document', 'analysis', 'failure', user_id=user_id, 
                     resource_id=analysis_id, details='Task timeout')
        raise self.retry(countdown=60, exc=Exception("Task timeout, retrying..."))
        
    except ValueError as e:
        logger.error(f"Validation error in task {self.request.id}: {str(e)}")
        if analysis_id and db:
            update_analysis_status(db, analysis_id, "failed", error_message=str(e))
            log_audit(db, 'analyze_document', 'analysis', 'failure', user_id=user_id,
                     resource_id=analysis_id, details=f'Validation error: {str(e)}')
        
        return {
            'status': 'error',
            'error_type': 'validation_error',
            'message': str(e),
            'file_id': file_id
        }
        
    except Exception as e:
        logger.error(f"Error in task {self.request.id}: {str(e)}", exc_info=True)
        
        if analysis_id and db:
            update_analysis_status(db, analysis_id, "failed", error_message=str(e))
            log_audit(db, 'analyze_document', 'analysis', 'failure', user_id=user_id,
                     resource_id=analysis_id, details=f'Error: {str(e)}')
        
        # Retry with exponential backoff
        raise self.retry(
            countdown=2 ** self.request.retries,
            exc=e
        )
        
    finally:
        if db:
            db.close()


@app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=120,  # 2 minutes for verification
    time_limit=180,  # 3 minutes hard limit
    name='tasks.verify_document_task'
)
def verify_document_task(
    self,
    file_path: str,
    file_id: str,
    analysis_id: int = None,
    user_id: int = None
) -> dict:
    """
    Celery task to verify financial document
    
    Args:
        file_path: Path to the PDF file
        file_id: Unique file identifier
        analysis_id: Database analysis record ID
        user_id: User ID
        
    Returns:
        Verification result
    """
    db = None
    try:
        db = next(get_db())
        logger.info(f"Starting verification task {self.request.id}")
        
        is_valid = validate_pdf_file(file_path)
        
        if analysis_id and db:
            log_audit(
                db,
                action='verify_document',
                resource_type='analysis',
                resource_id=analysis_id,
                status='success' if is_valid else 'failure',
                user_id=user_id
            )
        
        return {
            'status': 'success',
            'file_id': file_id,
            'is_valid': is_valid,
            'task_id': self.request.id
        }
        
    except Exception as e:
        logger.error(f"Verification task {self.request.id} failed: {str(e)}")
        if analysis_id and db:
            log_audit(db, 'verify_document', 'analysis', 'failure', user_id=user_id,
                     resource_id=analysis_id, details=str(e))
        raise self.retry(countdown=10, exc=e)
        
    finally:
        if db:
            db.close()


@app.task(name='tasks.cleanup_old_files')
def cleanup_old_files():
    """
    Periodic task to clean up old analysis files (24+ hours old)
    Reduces storage usage and maintains disk space
    """
    data_dir = Path('data')
    current_time = time.time()
    older_than = 86400  # 24 hours in seconds
    
    count = 0
    errors = 0
    
    try:
        for file_path in data_dir.glob('financial_document_*.pdf'):
            try:
                if current_time - os.path.getmtime(file_path) > older_than:
                    os.remove(file_path)
                    count += 1
                    logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to clean up {file_path}: {str(e)}")
                errors += 1
        
        logger.info(f"Cleanup task completed. Removed {count} files, {errors} errors")
        return {'cleaned_count': count, 'errors': errors}
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}


# Task monitoring and metrics
@app.task(bind=True)
def get_task_info(self):
    """Get current task information"""
    return {
        'task_id': self.request.id,
        'name': self.request.task,
        'args': self.request.args,
        'kwargs': self.request.kwargs,
        'is_eager': self.request.is_eager,
        'hostname': self.request.hostname
    }
