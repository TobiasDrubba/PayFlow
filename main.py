from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from service import TransactionService
import os
from pathlib import Path


# Initialize FastAPI app
app = FastAPI(title="WeAli Payment Overview", description="Transaction overview for WeChat and Alipay")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")

# Initialize service layer
transaction_service = TransactionService()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, message: str = None, success: bool = True):
    """Main page showing transaction overview and upload form"""
    
    # Get transaction summary
    summary = transaction_service.get_transaction_summary()
    
    # Get recent transactions (last 50)
    all_transactions = transaction_service.get_all_transactions()
    recent_transactions = sorted(all_transactions, key=lambda t: t.timestamp, reverse=True)[:50]
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "summary": summary,
        "transactions": recent_transactions,
        "message": message,
        "success": success
    })


@app.post("/upload")
async def upload_file(
    request: Request,
    csv_file: UploadFile = File(...),
    source_type: str = Form(...)
):
    """Handle CSV file upload and processing"""
    
    try:
        # Validate file type
        if not csv_file.filename.endswith('.csv'):
            return RedirectResponse(
                url="/?message=Please upload a CSV file&success=false", 
                status_code=303
            )
        
        # Validate source type
        if source_type not in ['wechat', 'alipay']:
            return RedirectResponse(
                url="/?message=Invalid source type&success=false", 
                status_code=303
            )
        
        # Read file content
        csv_content = await csv_file.read()
        csv_text = csv_content.decode('utf-8')
        
        # Process the file
        transaction_count = transaction_service.process_uploaded_file(csv_text, source_type)
        
        message = f"Successfully uploaded {transaction_count} {source_type} transactions!"
        return RedirectResponse(
            url=f"/?message={message}&success=true", 
            status_code=303
        )
        
    except Exception as e:
        error_message = f"Error processing file: {str(e)}"
        return RedirectResponse(
            url=f"/?message={error_message}&success=false", 
            status_code=303
        )


@app.get("/api/transactions")
async def get_transactions():
    """API endpoint to get all transactions as JSON"""
    transactions = transaction_service.get_all_transactions()
    return {
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "timestamp": t.timestamp.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "currency": t.currency,
                "transaction_type": t.transaction_type,
                "source": t.source
            }
            for t in transactions
        ]
    }


@app.get("/api/summary")
async def get_summary():
    """API endpoint to get transaction summary as JSON"""
    return transaction_service.get_transaction_summary()


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=8000)