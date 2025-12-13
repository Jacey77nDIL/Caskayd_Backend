"""
Example Integration: How to add Payment Account Form to your main.py
"""

# ============================================================================
# STEP 1: Import the router at the top of main.py
# ============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from payment_account_form import router as payment_account_router
# ... other imports

# ============================================================================
# STEP 2: Create FastAPI app (if you haven't already)
# ============================================================================

app = FastAPI(
    title="Caskayd API",
    description="Creator payment and collaboration platform",
    version="1.0.0"
)

# ============================================================================
# STEP 3: Configure CORS (update origins for production)
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React dev server
        "http://localhost:8080",      # Vue dev server
        "http://localhost:5173",      # Vite dev server
        "https://yourdomain.com",     # Production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# STEP 4: Include all routers (in main.py or separate routes module)
# ============================================================================

# Payment Account Form Routes
app.include_router(payment_account_router)

# Other existing routes
app.include_router(auth_router)           # if you have auth routes
app.include_router(payment_router)        # if you have payment routes
app.include_router(payout_router)         # if you have payout routes
# ... other routers

# ============================================================================
# STEP 5: Add health check endpoint
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Caskayd API",
        "version": "1.0.0"
    }

# ============================================================================
# STEP 6: Add root endpoint (optional)
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to Caskayd API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# ============================================================================
# STEP 7: Error handling (optional but recommended)
# ============================================================================

from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

# ============================================================================
# STEP 8: Middleware for logging (optional)
# ============================================================================

import logging
from fastapi import Request
import time

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Time: {process_time:.3f}s"
    )
    
    return response

# ============================================================================
# STEP 9: Run the application (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on file changes (dev only)
    )


# ============================================================================
# COMPLETE EXAMPLE main.py
# ============================================================================

"""
Complete main.py example with all routes and middleware
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time

# Import routers
from payment_account_form import router as payment_account_router
from auth import router as auth_router  # Adjust import path
from payment_routes import router as payment_router  # Adjust import path
from payout_routes import router as payout_router  # Adjust import path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Caskayd Creator Platform API",
    description="Payment and collaboration platform for creators and businesses",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "https://yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} "
        f"- {response.status_code} "
        f"({process_time:.3f}s)"
    )
    
    return response

# Include routers
app.include_router(auth_router)
app.include_router(payment_router)
app.include_router(payout_router)
app.include_router(payment_account_router)  # Payment Account Form

# Exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Caskayd API",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Caskayd Creator Platform API",
        "docs": "http://localhost:8000/docs",
        "redoc": "http://localhost:8000/redoc"
    }

# Run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


# ============================================================================
# TESTING THE INTEGRATION
# ============================================================================

"""
After integration, test with these commands:

1. Check if API is running:
   curl http://localhost:8000/health

2. Check available banks:
   curl http://localhost:8000/api/payment-account/banks

3. Login to get token:
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "creator@example.com", "password": "password123"}'

4. Setup payment account:
   curl -X POST http://localhost:8000/api/payment-account/setup \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "account_number": "0690000031",
       "bank_code": "011"
     }'

5. View all available endpoints:
   Visit http://localhost:8000/docs (Swagger UI)
   Or http://localhost:8000/redoc (ReDoc)
"""


# ============================================================================
# DEPLOYMENT CHECKLIST
# ============================================================================

"""
Before deploying to production:

☐ Update CORS origins (replace localhost with your domain)
☐ Set DEBUG=False
☐ Configure database connection for production
☐ Set up environment variables (.env file)
☐ Configure Paystack API keys
☐ Set up proper logging
☐ Enable HTTPS
☐ Configure rate limiting
☐ Set up API key authentication for admin endpoints
☐ Test all payment workflows
☐ Set up monitoring and alerts
☐ Configure backup strategies
☐ Set up CI/CD pipeline
☐ Run security audit
"""
