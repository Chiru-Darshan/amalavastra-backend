"""
Invoice Router
Handles invoice generation, management, and PDF export
"""
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import date
from decimal import Decimal
from io import BytesIO

from schemas.invoices import (
    InvoiceCreate, InvoiceResponse, InvoiceStatus,
    InvoiceListParams, InvoiceGenerateFromOrder, InvoicePDFRequest
)
from schemas.base import DataResponse, MessageResponse, PaginatedResponse
from services.invoice_service import InvoiceService
from services.pdf_generator import pdf_generator
from dependencies.auth import (
    get_current_user, CurrentUser, RequirePermission
)
from schemas.auth import Permission


router = APIRouter()


@router.post("/generate", response_model=DataResponse[dict], status_code=status.HTTP_201_CREATED)
async def generate_invoice_from_order(
    request: InvoiceGenerateFromOrder,
    current_user: CurrentUser = Depends(RequirePermission(Permission.INVOICES_CREATE))
):
    """
    Generate an invoice from an existing order.
    
    **Permissions Required:** invoices:create
    
    - **order_id**: The order to generate invoice from
    - **include_tax**: Whether to include GST
    - **tax_rate**: Tax rate percentage (default 18%)
    - **discount_percent**: Optional discount percentage
    - **notes**: Additional notes
    - **terms**: Custom terms and conditions
    """
    invoice = await InvoiceService.create_invoice_from_order(
        order_id=request.order_id,
        tax_rate=request.tax_rate,
        discount_percent=request.discount_percent,
        notes=request.notes,
        terms=request.terms,
        created_by=current_user.id
    )
    
    return DataResponse(
        success=True,
        message="Invoice generated successfully",
        data=invoice
    )


@router.get("/", response_model=PaginatedResponse[dict])
async def list_invoices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[InvoiceStatus] = None,
    customer_id: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    current_user: CurrentUser = Depends(RequirePermission(Permission.INVOICES_READ))
):
    """
    List invoices with filters and pagination.
    
    **Permissions Required:** invoices:read
    """
    result = await InvoiceService.list_invoices(
        page=page,
        page_size=page_size,
        status=status.value if status else None,
        customer_id=customer_id,
        from_date=from_date,
        to_date=to_date
    )
    
    return PaginatedResponse(
        success=True,
        **result
    )


@router.get("/{invoice_id}", response_model=DataResponse[dict])
async def get_invoice(
    invoice_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.INVOICES_READ))
):
    """
    Get invoice by ID.
    
    **Permissions Required:** invoices:read
    """
    invoice = await InvoiceService.get_invoice(invoice_id)
    
    return DataResponse(
        success=True,
        data=invoice
    )


@router.get("/number/{invoice_number}", response_model=DataResponse[dict])
async def get_invoice_by_number(
    invoice_number: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.INVOICES_READ))
):
    """
    Get invoice by invoice number.
    
    **Permissions Required:** invoices:read
    """
    invoice = await InvoiceService.get_invoice_by_number(invoice_number)
    
    return DataResponse(
        success=True,
        data=invoice
    )


@router.get("/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.INVOICES_READ))
):
    """
    Download invoice as PDF.
    
    **Permissions Required:** invoices:read
    
    Returns a PDF file for download.
    """
    # Get invoice data
    invoice = await InvoiceService.get_invoice(invoice_id)
    
    # Generate PDF
    pdf_bytes = pdf_generator.generate_invoice_pdf(invoice)
    
    # Create streaming response
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice_{invoice['invoice_number']}.pdf"
        }
    )


@router.get("/{invoice_id}/preview")
async def preview_invoice_pdf(
    invoice_id: str,
    current_user: CurrentUser = Depends(RequirePermission(Permission.INVOICES_READ))
):
    """
    Preview invoice as PDF in browser.
    
    **Permissions Required:** invoices:read
    
    Returns a PDF file for inline display.
    """
    # Get invoice data
    invoice = await InvoiceService.get_invoice(invoice_id)
    
    # Generate PDF
    pdf_bytes = pdf_generator.generate_invoice_pdf(invoice)
    
    # Create streaming response for inline display
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=invoice_{invoice['invoice_number']}.pdf"
        }
    )


@router.put("/{invoice_id}/status", response_model=DataResponse[dict])
async def update_invoice_status(
    invoice_id: str,
    status: InvoiceStatus = Query(...),
    current_user: CurrentUser = Depends(RequirePermission(Permission.INVOICES_CREATE))
):
    """
    Update invoice status.
    
    **Permissions Required:** invoices:create
    """
    invoice = await InvoiceService.update_invoice_status(invoice_id, status)
    
    return DataResponse(
        success=True,
        message="Invoice status updated",
        data=invoice
    )


@router.post("/{invoice_id}/cancel", response_model=DataResponse[dict])
async def cancel_invoice(
    invoice_id: str,
    reason: Optional[str] = None,
    current_user: CurrentUser = Depends(RequirePermission(Permission.INVOICES_CREATE))
):
    """
    Cancel an invoice.
    
    **Permissions Required:** invoices:create
    
    - **reason**: Optional cancellation reason
    """
    invoice = await InvoiceService.cancel_invoice(invoice_id, reason)
    
    return DataResponse(
        success=True,
        message="Invoice cancelled successfully",
        data=invoice
    )
