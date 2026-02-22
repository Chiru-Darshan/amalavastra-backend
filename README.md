# Saree Business API v2.0

A professional-grade REST API for saree business management built with FastAPI.

## 🚀 Features

### Security
- **JWT Authentication** - Secure token-based authentication with access & refresh tokens
- **Role-Based Access Control (RBAC)** - Admin, Manager, Staff, and Viewer roles
- **Password Policy** - Configurable password strength requirements
- **Rate Limiting** - Protection against brute force attacks
- **Security Headers** - HSTS, XSS Protection, Content Security Policy
- **Input Validation** - Comprehensive request validation with Pydantic
- **Audit Logging** - Track all security events

### Business Features
- **Saree Inventory Management** - Full CRUD with stock tracking
- **Customer Management** - Customer profiles and order history
- **Order Processing** - Order lifecycle management
- **Payment Tracking** - Full and installment payment support
- **Invoice Generation** - Professional PDF invoices with GST
- **Business Analytics** - Revenue reports, sales trends, low stock alerts

## 📁 Project Structure

```
backend/
├── core/                   # Core application modules
│   ├── config.py          # Configuration management
│   ├── security.py        # Security utilities (JWT, hashing)
│   ├── exceptions.py      # Custom exception classes
│   └── logging.py         # Logging configuration
├── dependencies/           # FastAPI dependencies
│   └── auth.py            # Authentication dependencies
├── middleware/             # Custom middleware
│   └── security.py        # Security middleware
├── routers/               # API route handlers
│   ├── auth.py            # Authentication endpoints
│   ├── sarees.py          # Saree management
│   ├── customers.py       # Customer management
│   ├── orders.py          # Order management
│   ├── payments.py        # Payment management
│   ├── installments.py    # Installment plans
│   ├── invoices.py        # Invoice generation
│   └── analytics.py       # Business analytics
├── schemas/               # Pydantic models
│   ├── base.py            # Base response schemas
│   ├── auth.py            # Authentication schemas
│   ├── sarees.py          # Saree schemas
│   ├── customers.py       # Customer schemas
│   ├── orders.py          # Order schemas
│   ├── payments.py        # Payment schemas
│   ├── installments.py    # Installment schemas
│   └── invoices.py        # Invoice schemas
├── services/              # Business logic layer
│   ├── auth_service.py    # Authentication service
│   ├── invoice_service.py # Invoice generation service
│   └── pdf_generator.py   # PDF generation service
├── migrations/            # Database migrations
│   └── 002_auth_invoices.sql
├── database.py            # Database connection
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── .env.example          # Environment template
```

## 🛠 Installation

### Prerequisites
- Python 3.10+
- Supabase account and project

### Setup

1. **Clone and navigate to backend**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   copy .env.example .env
   # Edit .env with your settings
   ```

5. **Run database migrations**
   - Execute `migrations/002_auth_invoices.sql` in Supabase SQL Editor

6. **Start the server**
   ```bash
   uvicorn main:app --reload
   ```

## 🔐 Authentication

### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@sareeelegance.com",
  "password": "Admin@123"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Using the Token
Include in all requests:
```
Authorization: Bearer <access_token>
```

### Refresh Token
```bash
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

## 👥 Role Permissions

| Role    | Description                          |
|---------|--------------------------------------|
| Admin   | Full access to all features          |
| Manager | Manage inventory, orders, customers  |
| Staff   | Create orders, record payments       |
| Viewer  | Read-only access                     |

## 📄 API Documentation

- **Swagger UI**: http://localhost:8000/docs (development only)
- **ReDoc**: http://localhost:8000/redoc

## 🧾 Invoice Generation

### Generate Invoice from Order
```bash
POST /api/invoices/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "order_id": "uuid-here",
  "include_tax": true,
  "tax_rate": 18,
  "discount_percent": 5,
  "notes": "Thank you for your purchase!"
}
```

### Download PDF
```bash
GET /api/invoices/{invoice_id}/pdf
Authorization: Bearer <token>
```

## 📊 Analytics Endpoints

- `GET /api/analytics/dashboard` - Dashboard statistics
- `GET /api/analytics/monthly-revenue` - Monthly revenue breakdown
- `GET /api/analytics/low-stock` - Low stock alerts
- `GET /api/analytics/top-customers` - Top customers by spending
- `GET /api/analytics/sales-trend` - Daily sales trend

## 🔧 Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| SECRET_KEY | JWT signing key | Random |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiry | 30 |
| RATE_LIMIT_PER_MINUTE | Rate limit | 60 |
| CORS_ORIGINS | Allowed origins | localhost |
| LOG_LEVEL | Logging level | INFO |

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=.
```

## 📝 License

MIT License

## 🤝 Support

For support, email support@sareeelegance.com
