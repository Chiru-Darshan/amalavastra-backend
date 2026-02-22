"""
Sarees Router
Handles saree inventory management
"""
from fastapi import APIRouter, Depends, Query, status, UploadFile, File
from typing import Optional, List
from decimal import Decimal

from database import supabase_admin as supabase
from schemas.sarees import SareeCreate, SareeUpdate, SareeResponse, SareeListParams
from schemas.base import DataResponse, MessageResponse, PaginatedResponse
from dependencies.auth import get_current_user, CurrentUser, RequirePermission
from schemas.auth import Permission
from core.exceptions import ResourceNotFoundError
from core.logging import logger
from services.storage_service import upload_image, upload_base64_image


router = APIRouter()


# Static fabric types - can be extended
FABRIC_TYPES = [
    "Silk", "Cotton", "Chiffon", "Georgette", "Crepe", "Satin", 
    "Organza", "Linen", "Net", "Velvet", "Banarasi", "Kanjivaram",
    "Tussar", "Chanderi", "Bhagalpuri", "Patola", "Pochampally"
]

COLORS = [
    "Red", "Blue", "Green", "Yellow", "Pink", "Purple", "Orange",
    "Black", "White", "Gold", "Silver", "Maroon", "Navy", "Teal",
    "Beige", "Brown", "Coral", "Magenta", "Peach", "Turquoise"
]


@router.get("/fabric-types", response_model=DataResponse[list])
async def get_fabric_types(
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_READ))
):
    """
    Get list of available fabric types.
    
    **Permissions Required:** sarees:read
    """
    # Get unique fabric types from database
    result = supabase.table("sarees").select("fabric_type").execute()
    db_fabrics = set()
    for item in (result.data or []):
        if item.get("fabric_type"):
            db_fabrics.add(item["fabric_type"])
    
    # Combine with predefined types
    all_fabrics = sorted(set(FABRIC_TYPES) | db_fabrics)
    
    return DataResponse(success=True, data=all_fabrics)


@router.get("/colors", response_model=DataResponse[list])
async def get_colors(
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_READ))
):
    """
    Get list of available colors.
    
    **Permissions Required:** sarees:read
    """
    # Get unique colors from database
    result = supabase.table("sarees").select("color").execute()
    db_colors = set()
    for item in (result.data or []):
        if item.get("color"):
            db_colors.add(item["color"])
    
    # Combine with predefined colors
    all_colors = sorted(set(COLORS) | db_colors)
    
    return DataResponse(success=True, data=all_colors)


@router.get("/vendors", response_model=DataResponse[list])
async def get_vendors(
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_READ))
):
    """
    Get list of vendors.
    
    **Permissions Required:** sarees:read
    """
    result = supabase.table("sarees").select("vendor_name").execute()
    vendors = set()
    for item in (result.data or []):
        if item.get("vendor_name"):
            vendors.add(item["vendor_name"])
    
    return DataResponse(success=True, data=sorted(vendors))


@router.get("/batches", response_model=DataResponse[list])
async def get_batches(
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_READ))
):
    """
    Get list of batch numbers.
    
    **Permissions Required:** sarees:read
    """
    result = supabase.table("sarees").select("batch_number").execute()
    batches = set()
    for item in (result.data or []):
        if item.get("batch_number"):
            batches.add(item["batch_number"])
    
    return DataResponse(success=True, data=sorted(batches))


@router.get("/", response_model=PaginatedResponse[dict])
async def get_sarees(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    published: Optional[bool] = None,
    fabric_type: Optional[str] = None,
    color: Optional[str] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    in_stock: Optional[bool] = None,
    search: Optional[str] = None,
    vendor_name: Optional[str] = None,
    batch_number: Optional[str] = None,
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_READ))
):
    """
    Get all sarees with filters and pagination.
    
    **Permissions Required:** sarees:read
    """
    query = supabase.table("sarees").select("*", count="exact")
    
    if published is not None:
        query = query.eq("is_published", published)
    if fabric_type:
        query = query.eq("fabric_type", fabric_type)
    if color:
        query = query.eq("color", color)
    if min_price is not None:
        query = query.gte("selling_price", float(min_price))
    if max_price is not None:
        query = query.lte("selling_price", float(max_price))
    if in_stock is not None:
        if in_stock:
            query = query.gt("stock_count", 0)
        else:
            query = query.eq("stock_count", 0)
    if search:
        query = query.ilike("name", f"%{search}%")
    if vendor_name:
        query = query.eq("vendor_name", vendor_name)
    if batch_number:
        query = query.eq("batch_number", batch_number)
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
    
    result = query.execute()
    total = result.count or 0
    total_pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        success=True,
        data=result.data or [],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


@router.get("/{saree_id}", response_model=DataResponse[dict])
async def get_saree(
    saree_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_READ))
):
    """
    Get a specific saree by ID.
    
    **Permissions Required:** sarees:read
    """
    data = supabase.table("sarees").select("*").eq("id", saree_id).execute().data
    if not data:
        raise ResourceNotFoundError("Saree", saree_id)
    
    return DataResponse(success=True, data=data[0])


@router.post("/", response_model=DataResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_saree(
    saree: SareeCreate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_CREATE))
):
    """
    Create a new saree.
    
    **Permissions Required:** sarees:create
    """
    saree_data = saree.model_dump()
    
    # Handle base64 image uploads
    if saree_data.get("images"):
        uploaded_urls = []
        for img_data in saree_data["images"]:
            # If it's already a URL, keep it
            if img_data.startswith("http"):
                uploaded_urls.append(img_data)
            # If it's base64, upload it
            elif "base64," in img_data or len(img_data) > 500:
                try:
                    url = await upload_base64_image(img_data)
                    uploaded_urls.append(url)
                except Exception as e:
                    logger.error(f"Failed to upload image: {str(e)}")
                    # Continue with other images
        saree_data["images"] = uploaded_urls
    
    # Convert Decimal to float for JSON serialization
    if saree_data.get("cost_price"):
        saree_data["cost_price"] = float(saree_data["cost_price"])
    if saree_data.get("selling_price"):
        saree_data["selling_price"] = float(saree_data["selling_price"])
    
    result = supabase.table("sarees").insert(saree_data).execute()
    
    logger.info(f"Saree created by user {current_user.id}: {saree.name}")
    
    return DataResponse(
        success=True,
        message="Saree created successfully",
        data=result.data[0] if result.data else None
    )


@router.put("/{saree_id}", response_model=DataResponse[dict])
async def update_saree(
    saree_id: str,
    saree: SareeUpdate,
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_UPDATE))
):
    """
    Update an existing saree.
    
    **Permissions Required:** sarees:update
    """
    # Check if saree exists
    existing = supabase.table("sarees").select("id").eq("id", saree_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Saree", saree_id)
    
    # Filter out None values
    update_data = {k: v for k, v in saree.model_dump().items() if v is not None}
    
    # Handle base64 image uploads
    if update_data.get("images"):
        uploaded_urls = []
        for img_data in update_data["images"]:
            # If it's already a URL, keep it
            if img_data.startswith("http"):
                uploaded_urls.append(img_data)
            # If it's base64, upload it
            elif "base64," in img_data or len(img_data) > 500:
                try:
                    url = await upload_base64_image(img_data)
                    uploaded_urls.append(url)
                except Exception as e:
                    logger.error(f"Failed to upload image: {str(e)}")
                    # Continue with other images
        update_data["images"] = uploaded_urls
    
    # Convert Decimal to float
    if update_data.get("cost_price"):
        update_data["cost_price"] = float(update_data["cost_price"])
    if update_data.get("selling_price"):
        update_data["selling_price"] = float(update_data["selling_price"])
    
    result = supabase.table("sarees").update(update_data).eq("id", saree_id).execute()
    
    return DataResponse(
        success=True,
        message="Saree updated successfully",
        data=result.data[0] if result.data else None
    )


@router.delete("/{saree_id}", response_model=MessageResponse)
async def delete_saree(
    saree_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_DELETE))
):
    """
    Delete a saree.
    
    **Permissions Required:** sarees:delete
    """
    # Check if saree exists
    existing = supabase.table("sarees").select("id").eq("id", saree_id).execute()
    if not existing.data:
        raise ResourceNotFoundError("Saree", saree_id)
    
    supabase.table("sarees").delete().eq("id", saree_id).execute()
    
    logger.info(f"Saree deleted by user {current_user.id}: {saree_id}")
    
    return MessageResponse(
        success=True,
        message="Saree deleted successfully"
    )


@router.post("/upload-images", response_model=DataResponse[dict], status_code=status.HTTP_201_CREATED)
async def upload_saree_images(
    files: List[UploadFile] = File(...),
    current_user: CurrentUser = Depends(RequirePermission(Permission.SAREES_CREATE))
):
    """
    Upload saree images to Cloudinary.
    
    **Permissions Required:** sarees:create
    
    Returns URLs of uploaded images.
    """
    if len(files) > 10:
        return DataResponse(
            success=False,
            message="Maximum 10 images allowed per upload",
            data=None
        )
    
    uploaded_urls = []
    for file in files:
        url = await upload_image(file)
        uploaded_urls.append(url)
    
    logger.info(f"Uploaded {len(uploaded_urls)} images by user {current_user.id}")
    
    return DataResponse(
        success=True,
        message=f"{len(uploaded_urls)} image(s) uploaded successfully",
        data={"urls": uploaded_urls}
    )
