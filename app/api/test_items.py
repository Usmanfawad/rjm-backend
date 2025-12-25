"""API endpoints for test items CRUD operations.

NOTE: This endpoint is disabled when using Supabase REST API.
The test_items table is not created in Supabase by default.
To enable, create the test_items table in Supabase and uncomment the endpoints.
"""

from fastapi import APIRouter, HTTPException, status

from app.config.logger import app_logger
from app.utils.responses import SuccessResponse, success_response


router = APIRouter(prefix="/v1/test-items", tags=["test-items"])


@router.get("/status")
async def test_items_status():
    """Check test items endpoint status.
    
    Test items CRUD is disabled when using Supabase REST API.
    Create the test_items table in Supabase to enable full functionality.
    """
    return success_response(
    data={"status": "disabled", "reason": "Using Supabase REST API"},
    message="Test items endpoint is disabled. See supabase/schema.sql for table setup."
    )
