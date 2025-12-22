"""API endpoints for test items CRUD operations."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select as sql_select

from app.db.db import get_session
from app.config.logger import app_logger
from app.models.test_item import (
    TestItem,
    TestItemCreate,
    TestItemUpdate,
    TestItemResponse,
)
from app.utils.responses import (
    SuccessResponse,
    PaginatedResponse,
    success_response,
    paginated_response,
)


router = APIRouter(prefix="/v1/test-items", tags=["test-items"])


@router.post("", response_model=SuccessResponse[TestItemResponse], status_code=status.HTTP_201_CREATED)
async def create_test_item(
    item: TestItemCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new test item."""
    try:
        db_item = TestItem(**item.model_dump())
        session.add(db_item)
        await session.commit()
        await session.refresh(db_item)
        
        app_logger.info(f"Created test item with id: {db_item.id}")
        item_response = TestItemResponse.model_validate(db_item)
        return success_response(
            data=item_response,
            message="Test item created successfully"
        )
        
    except Exception as e:
        await session.rollback()
        app_logger.error(f"Failed to create test item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test item: {str(e)}"
        )


@router.get("", response_model=PaginatedResponse[TestItemResponse])
async def get_test_items(
    page: int = 1,
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
):
    """Get all test items with pagination."""
    try:
        # Validate pagination parameters
        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10
        
        skip = (page - 1) * limit
        
        # Get total count
        count_stmt = select(func.count()).select_from(TestItem)
        total_result = await session.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Get paginated items
        statement = sql_select(TestItem).offset(skip).limit(limit).order_by(TestItem.created_at.desc())
        result = await session.execute(statement)
        items = result.scalars().all()
        
        items_response = [TestItemResponse.model_validate(item) for item in items]
        return paginated_response(
            data=items_response,
            page=page,
            limit=limit,
            total=total,
            message="Test items retrieved successfully"
        )
    except Exception as e:
        app_logger.error(f"Failed to fetch test items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test items: {str(e)}"
        )


@router.get("/{item_id}", response_model=SuccessResponse[TestItemResponse])
async def get_test_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific test item by ID."""
    try:
        statement = sql_select(TestItem).where(TestItem.id == item_id)
        result = await session.execute(statement)
        item = result.scalar_one_or_none()
        
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test item with id {item_id} not found"
            )
        
        item_response = TestItemResponse.model_validate(item)
        return success_response(
            data=item_response,
            message="Test item retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Failed to fetch test item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch test item: {str(e)}"
        )


@router.put("/{item_id}", response_model=SuccessResponse[TestItemResponse])
async def update_test_item(
    item_id: int,
    item_update: TestItemUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a test item by ID."""
    try:
        statement = sql_select(TestItem).where(TestItem.id == item_id)
        result = await session.execute(statement)
        item = result.scalar_one_or_none()
        
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test item with id {item_id} not found"
            )
        
        # Update only provided fields
        update_data = item_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        from datetime import datetime, timezone
        item.updated_at = datetime.now(timezone.utc)
        
        session.add(item)
        await session.commit()
        await session.refresh(item)
        
        app_logger.info(f"Updated test item with id: {item_id}")
        item_response = TestItemResponse.model_validate(item)
        return success_response(
            data=item_response,
            message="Test item updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        app_logger.error(f"Failed to update test item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update test item: {str(e)}"
        )


@router.delete("/{item_id}", response_model=SuccessResponse[dict], status_code=status.HTTP_200_OK)
async def delete_test_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a test item by ID."""
    try:
        statement = sql_select(TestItem).where(TestItem.id == item_id)
        result = await session.execute(statement)
        item = result.scalar_one_or_none()
        
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test item with id {item_id} not found"
            )
        
        await session.delete(item)
        await session.commit()
        
        app_logger.info(f"Deleted test item with id: {item_id}")
        return success_response(
            data={"id": item_id},
            message="Test item deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        app_logger.error(f"Failed to delete test item {item_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete test item: {str(e)}"
        )
