# Zerox Network

A full-stack Django-based print shop aggregation platform that connects customers with nearby print shops. Customers can upload files, configure print settings, pay online, and pick up orders using a secure PIN verification system.

---

## Table of Contents

- [Features](#features)
- [Screenshots / Demo](#screenshots--demo)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [Running Tests](#running-tests)
- [Workflow](#workflow)
- [Order Status Lifecycle](#order-status-lifecycle)
- [User Roles & Permissions](#user-roles--permissions)
- [URL Routes](#url-routes)
- [Database Models](#database-models)
- [Payment Integration](#payment-integration)
- [Payment Flow](#payment-flow)
- [File Upload Security](#file-upload-security)
- [Geolocation & Maps](#geolocation--maps)
- [Payout System](#payout-system)
- [Deployment](#deployment)
- [Production Checklist](#production-checklist)
- [Roadmap](#roadmap)
- [Known Limitations](#known-limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Customer
- Browse and search nearby print shops with **distance sorting**
- **Interactive map view** with Leaflet/OpenStreetMap
- **Geolocation** — detect user location or search places
- **Distance filter** (1km, 3km, 5km, 10km, 25km, Any)
- Upload multiple files (PDF, JPG, JPEG, PNG)
- Configure per-file print settings (paper size, color, copies, sides, pages per sheet)
- Online payment via Razorpay (UPI, Cards, Netbanking, Wallets)
- Real-time order tracking
- Secure PIN-based pickup verification
- Dispute resolution within 48 hours

### Shop Owner
- Register shop with **interactive map pin** for location
- **Multiple shops per user** support
- **Update shop location** with interactive map
- QR code generation (PNG + PDF poster)
- Dashboard with order management
- Accept / Reject / Mark Ready / Complete orders
- Financial earnings overview with commission tracking
- Shop image management (upload, set primary, delete)
- **Bank details** for receiving payouts
- **Payout history** viewing

### Admin / Staff
- Dashboard with platform analytics
- Shop approval workflow (approve, reject, suspend)
- **Edit shop location** with interactive map
- User management (view, edit, block/unblock, add staff)
- Image moderation
- Dispute resolution with refund processing
- **Automated daily payout processing** via RazorpayX
- **Payout settings** configuration
- **Payout history** and retry failed payouts
- Commission rate configuration
- Audit log tracking

---

## Screenshots / Demo

> Screenshots coming soon. Run the project locally to see all features.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLIENT BROWSER                     │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                  DJANGO WEB SERVER                    │
│                    (manage.py)                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│  │   core   │  │  shops   │  │  orders  │  │ admin_portal │
│  │  (Auth)  │  │  (Shop)  │  │ (Orders) │  │   (Admin)    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘
│       │              │              │                │
│       └──────────────┴──────────────┴────────────────┘
│                              │
│                              ▼
│                    ┌─────────────────┐
│                    │   SQLite DB     │
│                    │  (db.sqlite3)   │
│                    └─────────────────┘
│                              │
│                              ▼
│                    ┌─────────────────┐
│                    │   Media Files   │
│                    │  (uploads/qr)   │
│                    └─────────────────┘
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│              EXTERNAL SERVICES                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │   Razorpay   │  │  RazorpayX   │  │ Nominatim │  │
│  │  (Payments)  │  │   (Payouts)  │  │(Geocoding)│  │
│  └──────────────┘  └──────────────┘  └───────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  ReportLab   │  │    PyPDF2    │  │  Leaflet  │  │
│  │(PDF Poster)  │  │ (PDF Read)   │  │  (Maps)   │  │
│  └──────────────┘  └──────────────┘  └───────────┘  │
└─────────────────────────────────────────────────────┘
```

### Request Flow

```
Customer → Shop List (with map/distance) → Shop Detail (with map)
    → Upload Files → Configure Settings → Checkout → Razorpay Payment
    → Order Created → Shop Notified → Shop Accepts → Prints
    → Marks Ready (PIN Generated) → Customer Picks Up
    → Shop Verifies PIN → Order Completed → Payout Released
```

---

## Tech Stack

| Layer              | Technology                           |
|--------------------|--------------------------------------|
| Backend            | Django 4.2+ / Python 3.x            |
| Database           | SQLite3 (dev) / PostgreSQL (prod)   |
| Frontend           | HTML5, CSS3, JavaScript              |
| Fonts              | Manrope (Google Fonts)              |
| Maps               | Leaflet.js + OpenStreetMap          |
| Geocoding          | Nominatim (OpenStreetMap)           |
| Payments           | Razorpay Gateway                    |
| Payouts            | RazorpayX (Razorpay Payouts API)   |
| PDF Generation     | ReportLab                           |
| PDF Reading        | PyPDF2                              |
| QR Codes           | qrcode (Python library)             |
| Image Handling     | Pillow                              |
| HTTP Client        | Requests                            |
| Deployment         | Render (via render.yaml)            |

---

## Project Structure

```
Zerox_Network/
├── manage.py                    # Django management script
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render deployment config
├── db.sqlite3                   # SQLite database (dev)
├── .gitignore
│
├── zerox_project/               # Project configuration
│   ├── __init__.py
│   ├── settings.py              # Django settings
│   ├── urls.py                  # Root URL configuration
│   ├── wsgi.py                  # WSGI entry point
│   └── asgi.py                  # ASGI entry point
│
├── core/                        # Core app (Auth & User Management)
│   ├── models.py                # UserProfile model
│   ├── views.py                 # Signup, Login, Logout, Dashboard routing
│   ├── urls.py                  # Core URL patterns
│   ├── admin.py                 # Admin registration
│   ├── apps.py                  # App configuration
│   ├── decorators.py            # Role-based access decorators
│   ├── signals.py               # Auto-create UserProfile on User creation
│   ├── staff_management.py      # Staff management utilities
│   ├── admin_urls.py            # Admin-specific URLs
│   ├── admin_views.py           # Admin-specific views
│   └── migrations/
│
├── shops/                       # Shops app (Shop Management)
│   ├── models.py                # Shop, ShopImage, BankDetails models
│   ├── views.py                 # Shop CRUD, QR views, Order actions
│   ├── urls.py                  # Shop URL patterns
│   ├── forms.py                 # ShopImageForm
│   ├── qr_generator.py          # QR code generation (qrcode library)
│   ├── poster_generator.py      # PDF poster generation (ReportLab)
│   ├── settings_views.py        # Shop settings view
│   ├── geocoding.py             # Nominatim geocoding utilities
│   ├── api_views.py             # Geocoding & map API endpoints
│   ├── razorpay_payout.py       # RazorpayX payout integration
│   ├── bank_views.py            # Bank details & payout history views
│   ├── admin.py                 # Admin registration
│   ├── apps.py                  # App configuration
│   └── migrations/
│
├── orders/                      # Orders app (Order Processing)
│   ├── models.py                # Order, OrderFile, Dispute, Refund, AuditLog, Payout
│   ├── views.py                 # File upload, Configure, Checkout, Payment
│   ├── urls.py                  # Order URL patterns
│   ├── management/
│   │   └── commands/
│   │       └── process_daily_payouts.py  # Daily payout command
│   ├── admin.py                 # Admin registration
│   ├── apps.py                  # App configuration
│   └── migrations/
│
├── admin_portal/                # Admin Portal app (Platform Admin)
│   ├── models.py                # PayoutConfig singleton model
│   ├── views.py                 # Dashboard, Shop/User/Financial/Payout management
│   ├── urls.py                  # Admin portal URL patterns
│   ├── admin.py                 # Admin registration
│   ├── apps.py                  # App configuration
│   └── migrations/
│
├── templates/                   # HTML Templates
│   ├── base.html                # Base template with navbar
│   ├── core/                    # Auth templates (home, login, signup, profile)
│   ├── shops/                   # Shop templates (list, detail, dashboard, etc.)
│   ├── orders/                  # Order templates (configure, checkout, pickup, etc.)
│   └── admin_portal/            # Admin templates (dashboard, users, etc.)
│
├── static/                      # Static Files
│   ├── css/
│   │   └── style.css            # Main stylesheet
│   ├── js/
│   │   └── main.js              # Client-side JavaScript
│   └── images/
│       └── shop_placeholder.png # Placeholder shop image
│
└── media/                       # User-uploaded files
    ├── uploads/orders/          # Customer uploaded files
    ├── shop_images/             # Shop photos
    ├── qr_codes/                # Generated QR codes
    └── order_proofs/            # Order proof images
```

---

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Zerox_Network.git
   cd Zerox_Network
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   ```bash
   # Windows
   .venv\Scripts\activate

   # macOS/Linux
   source .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a superuser (admin)**
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to set username, email, and password.

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

---

## Environment Variables

For production, set these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SETTINGS_MODULE` | Settings module | `zerox_project.settings` |
| `SECRET_KEY` | Django secret key | (insecure dev key) |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Allowed hostnames | `*` |
| `RAZORPAY_KEY_ID` | Razorpay public key | (test key) |
| `RAZORPAY_KEY_SECRET` | Razorpay secret key | (test secret) |
| `RAZORPAYX_ACCOUNT_NUMBER` | RazorpayX account for payouts | (required for payouts) |

---

## Running the Project

### Development Server

```bash
python manage.py runserver
```

The server starts at `http://127.0.0.1:8000/`

### Available URLs

| URL                       | Description                    |
|---------------------------|--------------------------------|
| `http://127.0.0.1:8000/` | Home page                     |
| `http://127.0.0.1:8000/admin/` | Django admin panel      |
| `http://127.0.0.1:8000/portal/dashboard/` | Custom admin portal |
| `http://127.0.0.1:8000/shop/list/` | Browse shops (map/list) |

### Running Tests

```bash
python manage.py test
```

### Processing Daily Payouts

```bash
python manage.py process_daily_payouts
```

---

## Workflow

### Customer Workflow

```
1. Sign Up / Login
       │
       ▼
2. Browse Shop List (/shop/list/)
   - Toggle between Map and List view
   - Search by location or place name
   - Filter by distance (1km - 25km)
   - Sort by distance or price
       │
       ▼
3. Select Shop → View Detail (/shop/<uuid>/)
   - View shop info, pricing, photos
   - See shop location on interactive map
       │
       ▼
4. Upload Files (/order/upload/<uuid>/)
   - Supports: PDF, JPG, JPEG, PNG
   - Multiple files supported
   - Auto page count detection for PDFs
       │
       ▼
5. Configure Print Settings (/order/configure/<id>/)
   - Per-file or apply-to-all settings:
     • Paper Size: A4 / A3
     • Color: B&W / Color
     • Print Side: Single / Double
     • Pages Per Sheet: 1, 2, 4, 6, 9
     • Print Type: All / Odd / Even pages
     • Copies: 1+
     • Special Notes
       │
       ▼
6. Checkout (/order/checkout/<id>/)
   - Review order summary
   - Price calculation
       │
       ▼
7. Payment via Razorpay (/order/payment/<id>/)
   - UPI, Cards, Netbanking, Wallets
   - Secure server-side verification
       │
       ▼
8. Order Status Tracking (/order/my-orders/)
   - PENDING → PAID → ACCEPTED → PRINTING → READY → COMPLETED
       │
       ▼
9. Pickup with PIN (/order/pickup/<id>/)
   - Display 4-digit PIN to shop owner
       │
       ▼
10. Shop Verifies PIN → Order Completed → Payout Released
```

### Shop Owner Workflow

```
1. Register Shop (/shop/register/)
   - Shop name, location, phone
   - Click on map to pin location
   - Auto-detect or search location
   - Set pricing (A4/A3, B&W/Color)
   - QR code auto-generated
       │
       ▼
2. Shop Dashboard (/shop/dashboard/)
   - View all orders (filter by status)
   - Financial overview (gross, commission, earnings, pending payout)
   - Bank details status alert
   - Multiple shop selector (if owner has multiple shops)
       │
       ▼
3. Order Management
   - Accept Order → Status: ACCEPTED
   - Reject Order → Status: REJECTED (refund triggered)
   - Mark Ready → Generates 4-digit PIN → Status: READY
   - Complete → Enter PIN from customer → Status: COMPLETED
       │
       ▼
4. QR Code Management
   - Download QR as PNG (/shop/qr/download/<uuid>/png/)
   - Download Poster as PDF (/shop/qr/download/<uuid>/poster/)
       │
       ▼
5. Bank Details & Payouts
   - Add bank account details (/shop/bank-details/)
   - View payout history (/shop/payouts/)
       │
       ▼
6. Shop Settings (/shop/dashboard/settings/)
7. Image Management (/shop/dashboard/images/)
   - Upload images (require admin approval)
   - Set primary image
   - Delete images
```

### Admin Workflow

```
1. Login → Admin Portal (/portal/dashboard/)
   - Overview: shops, orders, users, revenue
   - Pending actions queue
       │
       ▼
2. Shop Approvals (/portal/approvals/)
   - Review pending shops
   - Approve / Reject with reason
       │
       ▼
3. User Management (/portal/users/)
   - View / Edit / Block users
   - Add staff members
       │
       ▼
4. Financial Management
   - Transactions (/portal/transactions/)
   - Analytics (/portal/analytics/)
       │
       ▼
5. Payout Management
   - Payout Settings (/portal/payouts/settings/)
   - Payout History (/portal/payouts/history/)
   - Retry Failed Payouts
   - Manual Payout Processing
   - Daily Auto-Payout via Management Command
       │
       ▼
6. Dispute Resolution (/portal/disputes/)
   - Review disputes
   - Approve/Reject refunds
       │
       ▼
7. Image Moderation (/portal/images/review/)
   - Approve/Reject shop images
```

---

## Order Status Lifecycle

```
                    ┌─────────────┐
                    │   PENDING   │  (Order created, awaiting payment)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    PAID     │  (Payment confirmed)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │  ACCEPTED   │          │  REJECTED   │  (Shop rejects → refund)
       └──────┬──────┘          └──────┬──────┘
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │  PRINTING   │          │  REFUNDED   │  (Admin processes refund)
       └──────┬──────┘          └─────────────┘
              │
       ┌──────▼──────┐
      │    READY     │  (PIN generated, awaiting pickup)
       └──────┬──────┘
              │
       ┌──────▼──────┐
       │  COMPLETED  │  (Customer picked up, PIN verified)
       └──────┬──────┘
              │
       ┌──────▼──────┐
       │ PAYOUT_DONE │  (Payout released to shop)
       └─────────────┘

  ┌─────────────────────────────────────────┐
  │  DISPUTED → IN_REVIEW → RESOLVED        │
  │              (48-hour window)            │
  └─────────────────────────────────────────┘
```

---

## User Roles & Permissions

| Role | Access Level |
|------|-------------|
| **CUSTOMER** | Browse shops, upload files, place orders, track orders, raise disputes, view PIN for pickup |
| **SHOP** | Shop dashboard, manage orders, QR codes, images, settings, bank details, payout history |
| **STAFF** | Admin portal (read-only for financials, can recommend dispute outcomes) |
| **ADMIN** | Full access: approve/reject shops, manage users, process refunds/payouts, analytics, commission settings |

### Role-Based Access Decorators

| Decorator | Purpose |
|-----------|---------|
| `@role_required('ROLE1', 'ROLE2')` | Restricts view access by user role. Checks authentication, profile existence, block status, and role. |
| `@log_action('Action', 'Model', object_id)` | Logs actions to AuditLog with user, IP address, and timestamp. |

---

## URL Routes

### Core (`/`)
| Method | URL | View | Name |
|--------|-----|------|------|
| GET | `/` | `home` | `core:home` |
| GET/POST | `/signup/` | `signup` | `core:signup` |
| GET/POST | `/login/` | `user_login` | `core:login` |
| GET | `/logout/` | `user_logout` | `core:logout` |
| GET/POST | `/profile/` | `profile` | `core:profile` |
| GET | `/dashboard/` | `dashboard_router` | `core:dashboard` |

### Shops (`/shop/`)
| Method | URL | View | Name |
|--------|-----|------|------|
| GET/POST | `/shop/register/` | `register_shop` | `shops:register` |
| GET | `/shop/dashboard/` | `shop_dashboard` | `shops:dashboard` |
| GET | `/shop/list/` | `shop_list` | `shops:list` |
| GET | `/shop/<uuid>/` | `shop_detail` | `shops:detail` |
| POST | `/shop/order/<id>/accept/` | `accept_order` | `shops:accept_order` |
| POST | `/shop/order/<id>/reject/` | `reject_order` | `shops:reject_order` |
| POST | `/shop/order/<id>/ready/` | `mark_ready` | `shops:mark_ready` |
| POST | `/shop/order/<id>/complete/` | `complete_order` | `shops:complete_order` |
| GET | `/shop/<qr_code>/` | `shop_profile_by_qr` | `shops:profile_by_qr` |
| GET | `/shop/qr/download/<uuid>/png/` | `download_qr_png` | `shops:download_qr_png` |
| GET | `/shop/qr/download/<uuid>/poster/` | `download_qr_poster` | `shops:download_qr_poster` |
| GET/POST | `/shop/dashboard/images/` | `manage_shop_images` | `shops:manage_images` |
| POST | `/shop/dashboard/images/delete/<id>/` | `delete_image` | `shops:delete_image` |
| POST | `/shop/dashboard/images/primary/<id>/` | `set_primary_image` | `shops:set_primary_image` |
| GET/POST | `/shop/dashboard/settings/` | `shop_settings` | `shops:settings` |
| GET/POST | `/shop/bank-details/` | `bank_details` | `shops:bank_details` |
| GET | `/shop/payouts/` | `payout_history` | `shops:payout_history` |
| GET/POST | `/shop/dashboard/<uuid>/location/` | `update_shop_location` | `shops:update_location` |

### Shop API Endpoints (`/shop/api/`)
| Method | URL | View | Name |
|--------|-----|------|------|
| GET | `/shop/api/geocode/?address=<query>` | `geocode_address` | `shops:api_geocode` |
| GET | `/shop/api/search/?q=<query>` | `search_locations` | `shops:api_search` |
| GET | `/shop/api/markers/` | `shop_markers` | `shops:api_markers` |
| POST | `/shop/api/<uuid>/update-location/` | `update_shop_location` | `shops:api_update_location` |

### Orders (`/order/`)
| Method | URL | View | Name |
|--------|-----|------|------|
| POST | `/order/upload/<uuid>/` | `upload_file` | `orders:upload` |
| GET/POST | `/order/configure/<id>/` | `configure_order` | `orders:configure` |
| POST | `/order/add-files/<id>/` | `add_files_to_order` | `orders:add_files` |
| GET | `/order/checkout/<id>/` | `checkout` | `orders:checkout` |
| GET/POST | `/order/payment/<id>/` | `process_payment` | `orders:payment` |
| POST | `/order/payment/success/<id>/` | `payment_success` | `orders:payment_success` |
| GET | `/order/my-orders/` | `my_orders` | `orders:my_orders` |
| GET | `/order/pickup/<id>/` | `pickup_info` | `orders:pickup_info` |
| POST | `/order/verify-pin/` | `verify_pin` | `orders:verify_pin` |
| GET/POST | `/order/dispute/<id>/` | `raise_dispute` | `orders:raise_dispute` |

### Admin Portal (`/portal/`)
| Method | URL | View | Name |
|--------|-----|------|------|
| GET | `/portal/dashboard/` | `dashboard` | `admin_portal:dashboard` |
| POST | `/portal/approve-shop/<uuid>/` | `approve_shop` | `admin_portal:approve_shop` |
| POST | `/portal/approve-image/<id>/` | `approve_image` | `admin_portal:approve_image` |
| GET | `/portal/shops/` | `manage_shops` | `admin_portal:manage_shops` |
| POST | `/portal/shops/<uuid>/toggle/` | `toggle_shop_status` | `admin_portal:toggle_shop_status` |
| GET/POST | `/portal/shops/<uuid>/edit-location/` | `edit_shop_location` | `admin_portal:edit_shop_location` |
| GET | `/portal/approvals/` | `shop_approvals` | `admin_portal:shop_approvals` |
| POST | `/portal/reject-shop/<uuid>/` | `reject_shop_view` | `admin_portal:reject_shop` |
| POST | `/portal/suspend-shop/<uuid>/` | `suspend_shop_view` | `admin_portal:suspend_shop` |
| GET | `/portal/users/` | `users_list` | `admin_portal:users` |
| GET/POST | `/portal/users/add-staff/` | `add_staff` | `admin_portal:add_staff` |
| GET | `/portal/users/<id>/` | `view_user` | `admin_portal:view_user` |
| GET/POST | `/portal/users/<id>/edit/` | `edit_user` | `admin_portal:edit_user` |
| POST | `/portal/users/<id>/delete/` | `delete_user` | `admin_portal:delete_user` |
| POST | `/portal/users/<id>/block/` | `toggle_user_block` | `admin_portal:block_user` |
| GET | `/portal/transactions/` | `transactions` | `admin_portal:transactions` |
| GET | `/portal/analytics/` | `analytics_view` | `admin_portal:analytics` |
| GET | `/portal/disputes/` | `disputes_list` | `admin_portal:disputes` |
| GET/POST | `/portal/disputes/<id>/resolve/` | `resolve_dispute` | `admin_portal:resolve_dispute` |
| GET | `/portal/refunds/` | `refunds_list` | `admin_portal:refunds_list` |
| POST | `/portal/refunds/<id>/process/` | `process_refund` | `admin_portal:process_refund` |
| GET | `/portal/payouts/` | `payouts_list` | `admin_portal:payouts` |
| POST | `/portal/payouts/<uuid>/process/` | `process_payout` | `admin_portal:process_payout` |
| GET | `/portal/payouts/history/` | `payout_history` | `admin_portal:payout_history` |
| GET/POST | `/portal/payouts/settings/` | `payout_settings` | `admin_portal:payout_settings` |
| POST | `/portal/payouts/<uuid>/retry/` | `retry_payout` | `admin_portal:retry_payout` |
| GET/POST | `/portal/images/review/` | `review_images` | `admin_portal:review_images` |
| POST | `/portal/set-commission/` | `set_commission` | `admin_portal:set_commission` |

---

## Database Models

### Core App

#### UserProfile
| Field | Type | Description |
|-------|------|-------------|
| user | OneToOneField(User) | Linked Django user |
| role | CharField | CUSTOMER / SHOP / STAFF / ADMIN |
| phone | CharField | Contact number |
| is_blocked | BooleanField | Account block status |
| created_at | DateTimeField | Creation timestamp |

### Shops App

#### Shop
| Field | Type | Description |
|-------|------|-------------|
| id | UUIDField | Primary key |
| owner | ForeignKey(User) | Shop owner (supports multiple shops per user) |
| name | CharField | Shop name |
| location | CharField | Shop address |
| phone | CharField | Contact number |
| latitude | FloatField | Shop latitude (geolocation) |
| longitude | FloatField | Shop longitude (geolocation) |
| is_verified | BooleanField | Admin verification status |
| is_approved | BooleanField | Admin approval status |
| is_suspended | BooleanField | Suspension status |
| qr_code | CharField | Unique QR code identifier |
| a4_bw_price | DecimalField | A4 B&W price per page |
| a4_color_price | DecimalField | A4 Color price per page |
| a3_bw_price | DecimalField | A3 B&W price per page |
| a3_color_price | DecimalField | A3 Color price per page |
| rating | DecimalField | Shop rating |
| total_orders | IntegerField | Total completed orders |
| earnings_total | DecimalField | Lifetime gross earnings |
| paid_total | DecimalField | Total amount paid out |
| commission_rate | DecimalField | Platform commission % |
| opening_time | TimeField | Shop opening time |
| closing_time | TimeField | Shop closing time |

#### ShopImage
| Field | Type | Description |
|-------|------|-------------|
| shop | ForeignKey(Shop) | Parent shop |
| image | ImageField | Uploaded image |
| caption | CharField | Image caption |
| is_primary | BooleanField | Primary display image |
| is_approved | BooleanField | Admin approval status |

#### BankDetails
| Field | Type | Description |
|-------|------|-------------|
| shop | OneToOneField(Shop) | Linked shop |
| account_holder_name | CharField | Account holder name |
| account_number | CharField | Bank account number |
| ifsc_code | CharField | IFSC code |
| bank_name | CharField | Bank name |
| branch | CharField | Branch name |
| is_verified | BooleanField | Admin verification status |
| created_at | DateTimeField | Creation timestamp |
| updated_at | DateTimeField | Last update timestamp |

### Orders App

#### Order
| Field | Type | Description |
|-------|------|-------------|
| id | AutoField | Primary key |
| shop | ForeignKey(Shop) | Target shop |
| customer | ForeignKey(User) | Customer (nullable for guest orders) |
| customer_name | CharField | Customer name |
| customer_phone | CharField | Customer phone |
| final_sheets | IntegerField | Total print sheets |
| total_price | DecimalField | Order total |
| commission_amount | DecimalField | Platform commission |
| shop_payout | DecimalField | Shop earnings |
| status | CharField | Order status |
| pin_code | CharField | 4-digit pickup PIN |
| rejection_reason | TextField | Rejection reason |
| pickup_deadline | DateTimeField | Pickup deadline |
| dispute_window_expires | DateTimeField | Dispute window end |
| created_at | DateTimeField | Creation timestamp |
| paid_at | DateTimeField | Payment timestamp |
| completed_at | DateTimeField | Completion timestamp |

#### OrderFile
| Field | Type | Description |
|-------|------|-------------|
| order | ForeignKey(Order) | Parent order |
| file | FileField | Uploaded file |
| file_name | CharField | Original filename |
| file_size_mb | FloatField | File size in MB |
| pages_count | IntegerField | Number of pages |
| paper_size | CharField | A4 / A3 |
| color_type | CharField | BW / COLOR |
| print_side | CharField | SINGLE / DOUBLE |
| pages_per_sheet | IntegerField | 1, 2, 4, 6, 9 |
| print_type | CharField | ALL / ODD / EVEN |
| copies | PositiveIntegerField | Number of copies |
| special_note | TextField | Special instructions |
| price_per_sheet | DecimalField | Price per sheet |
| final_sheets | IntegerField | Calculated sheets |
| total_price | DecimalField | File total price |

#### Dispute
| Field | Type | Description |
|-------|------|-------------|
| order | ForeignKey(Order) | Disputed order |
| raised_by | ForeignKey(User) | Customer |
| issue_type | CharField | Issue category |
| description | TextField | Issue description |
| proof_image | ImageField | Evidence image |
| shop_response | TextField | Shop's response |
| status | CharField | PENDING / IN_REVIEW / RESOLVED / REJECTED |
| refund_approved | BooleanField | Refund decision |
| refund_amount | DecimalField | Refund amount |

#### Refund
| Field | Type | Description |
|-------|------|-------------|
| order | ForeignKey(Order) | Related order |
| amount | DecimalField | Refund amount |
| reason | CharField | Refund reason |
| status | CharField | PENDING / PROCESSING / COMPLETED / FAILED |
| processed_by | ForeignKey(User) | Admin who processed |

#### Payout
| Field | Type | Description |
|-------|------|-------------|
| id | UUIDField | Primary key |
| shop | ForeignKey(Shop) | Target shop |
| amount | DecimalField | Payout amount |
| status | CharField | PENDING / PROCESSING / COMPLETED / FAILED |
| razorpay_transfer_id | CharField | Razorpay transfer ID |
| failure_reason | TextField | Failure reason |
| processed_at | DateTimeField | Processing timestamp |
| created_at | DateTimeField | Creation timestamp |

#### AuditLog
| Field | Type | Description |
|-------|------|-------------|
| user | ForeignKey(User) | Action performer |
| action | CharField | Action description |
| model_name | CharField | Affected model |
| object_id | CharField | Affected object ID |
| details | TextField | Additional details |
| ip_address | GenericIPAddressField | Client IP |
| timestamp | DateTimeField | Action timestamp |

### Admin Portal App

#### PayoutConfig
| Field | Type | Description |
|-------|------|-------------|
| id | AutoField | Primary key (singleton) |
| auto_payout_enabled | BooleanField | Enable daily auto-payouts |
| payout_day | IntegerField | Day of month for payouts (1-28) |
| min_payout_amount | DecimalField | Minimum payout threshold |
| last_payout_date | DateTimeField | Last payout execution |

---

## Payment Integration

### Razorpay Gateway

Zerox Network uses **Razorpay** for payment processing.

#### Configuration (in `settings.py`)
```python
RAZORPAY_KEY_ID = 'rzp_test_...'      # Public key
RAZORPAY_KEY_SECRET = '...'            # Secret key
```

#### How It Works

1. **Frontend**: Razorpay Checkout.js loads payment modal
2. **Backend**: Creates Razorpay Order via API
3. **Payment**: Customer completes payment in modal
4. **Verification**: Server verifies payment signature using HMAC-SHA256
5. **Confirmation**: Order status updated, receipt generated

#### Payment Flow Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Customer   │     │   Zerox      │     │   Razorpay   │
│   Browser    │     │   Server     │     │   Gateway    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │  1. Click Pay      │                    │
       │───────────────────>│                    │
       │                    │                    │
       │                    │  2. Create Order   │
       │                    │───────────────────>│
       │                    │                    │
       │                    │  3. Order ID       │
       │                    │<───────────────────│
       │                    │                    │
       │  4. Razorpay Modal │                    │
       │<───────────────────│                    │
       │                    │                    │
       │  5. Payment Done   │                    │
       │───────────────────>│                    │
       │                    │                    │
       │                    │  6. Verify Payment │
       │                    │───────────────────>│
       │                    │                    │
       │                    │  7. Payment Verified│
       │                    │<───────────────────│
       │                    │                    │
       │  8. Order Confirmed│                    │
       │<───────────────────│                    │
```

#### Key Files
- `orders/views.py` → `process_payment()`, `payment_success()`
- `templates/orders/checkout.html` → Razorpay Checkout.js integration

---

## Payment Flow

### Complete Payment Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                     PAYMENT FLOW                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. CUSTOMER UPLOADS FILES                                   │
│     └─> Order created (status: PENDING)                      │
│                                                              │
│  2. CUSTOMER CONFIGURES PRINT SETTINGS                       │
│     └─> Price calculated per file                            │
│                                                              │
│  3. CUSTOMER REVIEWS CHECKOUT                                │
│     └─> Order total = Sum of all file prices                 │
│                                                              │
│  4. CUSTOMER CLICKS "PAY NOW"                                │
│     └─> Razorpay order created (server-side)                 │
│     └─> Razorpay Checkout.js modal opens                     │
│                                                              │
│  5. CUSTOMER COMPLETES PAYMENT IN MODAL                      │
│     └─> UPI / Card / Netbanking / Wallet                     │
│     └─> Razorpay returns: payment_id, order_id, signature    │
│                                                              │
│  6. PAYMENT SUCCESS CALLBACK                                  │
│     └─> Server verifies signature:                           │
│         HMAC-SHA256(order_id + "|" + payment_id, secret)     │
│     └─> If valid:                                            │
│         • Order status → PAID                                │
│         • Commission calculated (e.g., 10%)                  │
│         • Shop payout = Total - Commission                   │
│         • paid_at timestamp set                              │
│     └─> If invalid:                                          │
│         • Payment marked as failed                           │
│         • Error logged                                       │
│                                                              │
│  7. SHOP PROCESSES ORDER                                     │
│     └─> Accepts → Prints → Marks Ready (PIN generated)       │
│                                                              │
│  8. CUSTOMER PICKS UP                                        │
│     └─> Shows 4-digit PIN to shop                            │
│     └─> Shop enters PIN → Order COMPLETED                    │
│                                                              │
│  9. PAYOUT RELEASED                                          │
│     └─> Via RazorpayX transfer API                           │
│     └─> Transferred to shop's bank account                   │
│     └─> Order status → PAYOUT_DONE                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Price Calculation Example

```
File: report.pdf (10 pages)
Settings: A4, Color, Single-sided, 1 copy

Calculation:
  base_price    = A4 Color price × pages
                = ₹5.00 × 10 = ₹50.00

  double_side   = No (single-sided)

  pages_per_sheet = 1 (all pages)

  copies        = 1

  total_sheets  = 10 pages ÷ 1 × 1 = 10 sheets
  total_price   = 10 sheets × ₹5.00 = ₹50.00

Platform Commission (10%):
  commission    = ₹50.00 × 10% = ₹5.00
  shop_payout   = ₹50.00 - ₹5.00 = ₹45.00
```

### Payment Verification (Server-Side)

```python
import razorpay
from django.conf import settings

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def verify_payment(order_id, payment_id, signature):
    params_dict = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }
    
    try:
        client.utility.verify_payment_signature(params_dict)
        return True  # Payment verified
    except razorpay.errors.SignatureVerificationError:
        return False  # Payment verification failed
```

---

## File Upload Security

### Supported Formats
| Format | Extension | Max Size |
|--------|-----------|----------|
| PDF | `.pdf` | 50 MB |
| JPEG | `.jpg`, `.jpeg` | 10 MB |
| PNG | `.png` | 10 MB |

### Security Measures
- File type validation (server-side)
- File size limits
- Uploaded files stored outside web root
- PDF page count auto-detection (PyPDF2)
- Image dimensions validation for shop images

### Shop Image Validation (`shops/forms.py`)
| Rule | Value |
|------|-------|
| Max file size | 5 MB |
| Min resolution | 1280×720 pixels |
| Accepted formats | `image/*` |

---

## Geolocation & Maps

### Features
- **Interactive maps** using Leaflet.js + OpenStreetMap
- **Geocoding** via Nominatim (free, no API key)
- **Reverse geocoding** (coordinates → address)
- **Distance calculation** using Haversine formula
- **Distance filtering** (1km, 3km, 5km, 10km, 25km, Any)

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /shop/api/geocode/?address=<query>` | Geocode address to coordinates |
| `GET /shop/api/search/?q=<query>` | Search places |
| `GET /shop/api/markers/` | Get all shop markers for map |

### Haversine Distance Formula

```python
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c  # Distance in km
```

### Map Views
- **Shop List**: Toggle between map and list view
- **Shop Detail**: Interactive map showing shop location
- **Shop Registration**: Click to pin location, auto-detect GPS

---

## Payout System

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Zerox     │────>│  RazorpayX  │────>│ Shop Bank   │
│   Server    │     │   Payouts   │     │  Account    │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Razorpay Payouts API Flow

```
1. Admin configures payout settings
   └─> Auto-payout enabled, min amount, payout day

2. Daily management command runs
   └─> python manage.py process_daily_payouts

3. Command finds shops with pending payouts
   └─> Payout amount ≥ minimum threshold

4. For each shop:
   a. Fetch bank details from BankDetails model
   b. Create Razorpay contact (if not exists)
   c. Create fund account (bank account)
   d. Create payout transfer
   e. Update Payout model status

5. If payout succeeds:
   └─> Payout status → COMPLETED
   └─> Shop.paid_total updated

6. If payout fails:
   └─> Payout status → FAILED
   └─> Failure reason logged
   └─> Admin can retry from dashboard
```

### Payout Status Flow

```
PENDING → PROCESSING → COMPLETED
                │
                └──→ FAILED → (Retry) → PROCESSING → COMPLETED
```

### Key Files

| File | Description |
|------|-------------|
| `shops/razorpay_payout.py` | RazorpayX API integration |
| `shops/bank_views.py` | Bank details form, payout history |
| `orders/models.py` | Payout model |
| `admin_portal/models.py` | PayoutConfig singleton |
| `orders/management/commands/process_daily_payouts.py` | Daily payout command |
| `admin_portal/views.py` | Payout settings, history, retry |

### RazorpayX Configuration

```python
# settings.py
RAZORPAY_KEY_ID = 'rzp_test_...'
RAZORPAY_KEY_SECRET = '...'
RAZORPAYX_ACCOUNT_NUMBER = '...'  # Required for payouts
```

---

## Deployment

### Render (Production)

The project includes a `render.yaml` for Render deployment.

1. Push code to GitHub
2. Connect repository to Render
3. Render auto-detects Django and runs:
   ```bash
   pip install -r requirements.txt
   python manage.py collectstatic --noinput
   python manage.py migrate
   ```

### Manual Production Setup

```bash
# Set environment variables
export DJANGO_SETTINGS_MODULE=zerox_project.settings
export SECRET_KEY='your-secret-key'
export DEBUG=False
export ALLOWED_HOSTS='yourdomain.com'

# Database (switch to PostgreSQL)
pip install psycopg2-binary
# Update DATABASES in settings.py

# Run
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn zerox_project.wsgi:application
```

---

## Production Checklist

### Security
- [ ] Set `DEBUG=False`
- [ ] Generate new `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Set `SECURE_SSL_REDIRECT=True`
- [ ] Set `SESSION_COOKIE_SECURE=True`
- [ ] Set `CSRF_COOKIE_SECURE=True`
- [ ] Remove `RAZORPAY_KEY_SECRET` from code (use env vars)

### Database
- [ ] Switch to PostgreSQL
- [ ] Run `python manage.py migrate`
- [ ] Create superuser

### Razorpay
- [ ] Use production keys (not test keys)
- [ ] Configure RazorpayX account number
- [ ] Test payment flow end-to-end
- [ ] Test payout flow end-to-end

### Static Files
- [ ] Run `python manage.py collectstatic --no-input`
- [ ] Configure CDN (optional)

### Monitoring
- [ ] Set up error tracking (Sentry)
- [ ] Configure logging
- [ ] Monitor Razorpay dashboard

---

## Roadmap

### Completed
- [x] Customer upload & payment flow
- [x] Shop owner dashboard & order management
- [x] Admin portal with analytics
- [x] QR code & poster generation
- [x] Dispute resolution system
- [x] Image moderation
- [x] Bank details & payout system
- [x] RazorpayX integration
- [x] Geolocation & maps
- [x] Distance sorting & filtering
- [x] Interactive Leaflet map
- [x] Multiple shops per user
- [x] Daily auto-payout command

### Planned
- [ ] Email notifications (order status, payout confirmations)
- [ ] SMS notifications for order ready
- [ ] Shop reviews & ratings by customers
- [ ] Multi-language support
- [ ] Mobile app (React Native / Flutter)
- [ ] Advanced analytics dashboard
- [ ] Coupon & discount system
- [ ] Bulk order support
- [ ] API for third-party integrations
- [ ] Webhook support for Razorpay events

---

## Known Limitations

1. **SQLite** — Not suitable for production (use PostgreSQL)
2. **Geocoding** — Nominatim has rate limits (1 req/sec)
3. **File Storage** — Local filesystem (use S3 for production)
4. **Email** — Not configured (use SendGrid/Mailgun)
5. **SMS** — Not configured (use Twilio)
6. **Caching** — No Redis/Memcached configured

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is proprietary. All rights reserved.

---

**Built with Django for Zerox Network**
