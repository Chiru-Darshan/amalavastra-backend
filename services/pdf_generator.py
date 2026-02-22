"""
PDF Generator Service
Generate professional PDF invoices using ReportLab
"""
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from core.config import settings
from core.logging import logger


class PDFGenerator:
    """Professional PDF invoice generator"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=6,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#2d3748'),
            spaceBefore=12,
            spaceAfter=12,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#4a5568'),
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#718096'),
            spaceAfter=2
        ))
        
        self.styles.add(ParagraphStyle(
            name='RightAligned',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT
        ))
        
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#a0aec0'),
            alignment=TA_CENTER
        ))
    
    def generate_invoice_pdf(self, invoice: Dict[str, Any]) -> bytes:
        """Generate a professional PDF invoice"""
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        elements = []
        
        # Header with company info
        elements.extend(self._build_header(invoice))
        
        # Invoice details section
        elements.extend(self._build_invoice_details(invoice))
        
        # Customer info
        elements.extend(self._build_customer_section(invoice))
        
        # Items table
        elements.extend(self._build_items_table(invoice))
        
        # Totals section
        elements.extend(self._build_totals_section(invoice))
        
        # Payment info
        elements.extend(self._build_payment_info(invoice))
        
        # Terms and notes
        elements.extend(self._build_terms_section(invoice))
        
        # Footer
        elements.extend(self._build_footer(invoice))
        
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated PDF for invoice {invoice.get('invoice_number')}")
        
        return pdf_bytes
    
    def _build_header(self, invoice: Dict[str, Any]) -> list:
        """Build the header section"""
        elements = []
        
        # Company name
        elements.append(Paragraph(
            invoice.get('company_name', settings.COMPANY_NAME),
            self.styles['CompanyName']
        ))
        
        # Company details
        company_details = f"""
        {invoice.get('company_address', settings.COMPANY_ADDRESS)}<br/>
        Phone: {invoice.get('company_phone', settings.COMPANY_PHONE)} | 
        Email: {invoice.get('company_email', settings.COMPANY_EMAIL)}<br/>
        GSTIN: {invoice.get('company_gst', settings.COMPANY_GST)}
        """
        elements.append(Paragraph(company_details, self.styles['SmallText']))
        
        # Divider
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor('#1a365d'),
            spaceBefore=5,
            spaceAfter=10
        ))
        
        return elements
    
    def _build_invoice_details(self, invoice: Dict[str, Any]) -> list:
        """Build invoice details section"""
        elements = []
        
        elements.append(Paragraph("TAX INVOICE", self.styles['InvoiceTitle']))
        
        # Invoice info table
        invoice_data = [
            ['Invoice Number:', invoice.get('invoice_number', 'N/A')],
            ['Invoice Date:', self._format_date(invoice.get('issue_date'))],
            ['Due Date:', self._format_date(invoice.get('due_date')) or 'On Receipt'],
            ['Status:', invoice.get('status', 'ISSUED').upper()],
        ]
        
        table = Table(invoice_data, colWidths=[100, 150])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_customer_section(self, invoice: Dict[str, Any]) -> list:
        """Build customer information section"""
        elements = []
        
        elements.append(Paragraph("Bill To:", self.styles['SectionHeader']))
        
        customer_name = invoice.get('customer_name', 'Walk-in Customer')
        customer_address = invoice.get('customer_address', '')
        customer_phone = invoice.get('customer_phone', '')
        customer_email = invoice.get('customer_email', '')
        
        customer_info = f"<b>{customer_name}</b><br/>"
        if customer_address:
            customer_info += f"{customer_address}<br/>"
        if customer_phone:
            customer_info += f"Phone: {customer_phone}<br/>"
        if customer_email:
            customer_info += f"Email: {customer_email}"
        
        elements.append(Paragraph(customer_info, self.styles['NormalText']))
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_items_table(self, invoice: Dict[str, Any]) -> list:
        """Build items table"""
        elements = []
        
        elements.append(Paragraph("Items:", self.styles['SectionHeader']))
        
        # Table header
        header = ['#', 'Description', 'HSN', 'Qty', 'Unit Price', 'Tax %', 'Amount']
        
        # Table data
        items = invoice.get('items', [])
        data = [header]
        
        for idx, item in enumerate(items, 1):
            row = [
                str(idx),
                item.get('description', 'Item'),
                item.get('hsn_code', ''),
                str(item.get('quantity', 1)),
                self._format_currency(item.get('unit_price', 0)),
                f"{item.get('tax_percent', 0)}%",
                self._format_currency(item.get('total', 0))
            ]
            data.append(row)
        
        # Create table
        col_widths = [25, 180, 50, 35, 70, 45, 80]
        table = Table(data, colWidths=col_widths)
        
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1a365d')),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_totals_section(self, invoice: Dict[str, Any]) -> list:
        """Build totals section"""
        elements = []
        
        subtotal = invoice.get('subtotal', 0)
        discount = invoice.get('discount_amount', 0)
        tax = invoice.get('tax_amount', 0)
        total = invoice.get('total_amount', 0)
        paid = invoice.get('paid_amount', 0)
        due = invoice.get('due_amount', 0)
        
        totals_data = [
            ['Subtotal:', self._format_currency(subtotal)],
        ]
        
        if discount > 0:
            totals_data.append(['Discount:', f"- {self._format_currency(discount)}"])
        
        totals_data.extend([
            ['Tax (GST):', self._format_currency(tax)],
            ['Total Amount:', self._format_currency(total)],
        ])
        
        if paid > 0:
            totals_data.append(['Amount Paid:', f"- {self._format_currency(paid)}"])
        
        totals_data.append(['Amount Due:', self._format_currency(due)])
        
        table = Table(totals_data, colWidths=[380, 100])
        
        styles = [
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        
        # Highlight total and due rows
        total_row_idx = len(totals_data) - 2 if paid > 0 else len(totals_data) - 1
        due_row_idx = len(totals_data) - 1
        
        styles.extend([
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TOPPADDING', (0, -1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
        ])
        
        table.setStyle(TableStyle(styles))
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_payment_info(self, invoice: Dict[str, Any]) -> list:
        """Build payment information section"""
        elements = []
        
        elements.append(Paragraph("Payment Information:", self.styles['SectionHeader']))
        
        payment_info = """
        <b>Bank Transfer:</b><br/>
        Bank Name: State Bank of India<br/>
        Account Name: Amalavastra<br/>
        Account Number: 12345678901234<br/>
        IFSC Code: SBIN0001234<br/><br/>
        <b>UPI:</b> amalavastra@upi
        """
        
        elements.append(Paragraph(payment_info, self.styles['SmallText']))
        elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_terms_section(self, invoice: Dict[str, Any]) -> list:
        """Build terms and notes section"""
        elements = []
        
        # Notes
        notes = invoice.get('notes')
        if notes:
            elements.append(Paragraph("Notes:", self.styles['SectionHeader']))
            elements.append(Paragraph(notes, self.styles['SmallText']))
            elements.append(Spacer(1, 10))
        
        # Terms
        terms = invoice.get('terms')
        if terms:
            elements.append(Paragraph("Terms & Conditions:", self.styles['SectionHeader']))
            # Replace newlines with <br/> for proper rendering
            terms_formatted = terms.replace('\n', '<br/>')
            elements.append(Paragraph(terms_formatted, self.styles['SmallText']))
            elements.append(Spacer(1, 15))
        
        return elements
    
    def _build_footer(self, invoice: Dict[str, Any]) -> list:
        """Build footer section"""
        elements = []
        
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#e2e8f0'),
            spaceBefore=10,
            spaceAfter=10
        ))
        
        # Signature line
        signature_data = [
            ['', 'Authorized Signature'],
            ['', '_____________________'],
        ]
        
        table = Table(signature_data, colWidths=[350, 150])
        table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 20),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Footer text
        footer_text = f"""
        Thank you for your business!<br/>
        This is a computer-generated invoice and does not require a signature.<br/>
        Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
        """
        elements.append(Paragraph(footer_text, self.styles['Footer']))
        
        return elements
    
    def _format_currency(self, amount) -> str:
        """Format amount as currency"""
        try:
            return f"₹{float(amount):,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"
    
    def _format_date(self, date_str) -> Optional[str]:
        """Format date string"""
        if not date_str:
            return None
        try:
            if isinstance(date_str, str):
                # Try parsing ISO format
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime('%d %b %Y')
            return str(date_str)
        except ValueError:
            return str(date_str)


# Singleton instance
pdf_generator = PDFGenerator()
