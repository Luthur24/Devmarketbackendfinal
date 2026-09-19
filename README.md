DevMarket Backend

Backend infrastructure for DevMarket, a developer-focused marketplace for discovering, showcasing, and trading digital products, developer tools, and resources.

Overview

DevMarket Backend provides the server-side API and application logic behind the DevMarket platform.

The backend handles user authentication, developer profiles, product listings, categories, media uploads, marketplace discovery, and authenticated user operations.

The application is built with Flask and PostgreSQL and exposes a REST-oriented API consumed by the DevMarket frontend.

Core Features

Authentication & Accounts

- User registration and authentication
- Token-based authentication
- User profile management
- Developer profiles
- Profile information and skills
- GitHub, website, Twitter, and LinkedIn profile links
- Authenticated account operations

Marketplace

- Product listings
- Product categories
- Product search
- Category filtering
- Product-type filtering
- Sorting
- Pagination
- Product discovery
- Seller/developer information

The product endpoint supports pagination, search, category filtering, sorting, and product-type filtering.

Media Management

The backend integrates Cloudinary for image handling.

Authenticated users can upload:

- Product images
- Profile avatars

Uploaded media is processed through Cloudinary and returned as secure URLs for use by the application.

API Structure

Representative endpoints include:

POST   /api/auth/register
POST   /api/auth/login
PUT    /api/auth/update-profile
POST   /api/auth/logout

POST   /api/upload/image
POST   /api/upload/avatar

GET    /api/categories
GET    /api/products

The API uses authenticated middleware for operations that require an identified user.

Architecture

┌──────────────────────────┐
│    DevMarket Frontend    │
│       Web Interface      │
└────────────┬─────────────┘
             │
             │ HTTP / JSON
             ▼
┌──────────────────────────┐
│       Flask API          │
│                          │
│ Authentication           │
│ Profiles                 │
│ Products                 │
│ Categories               │
│ Search & Filtering       │
│ Media Uploads             │
└───────┬──────────┬───────┘
        │          │
        ▼          ▼
 PostgreSQL     Cloudinary
  Database         Media

Technology Stack

- Python
- Flask
- PostgreSQL
- REST API
- Token-based authentication
- Cloudinary
- Git & GitHub

Repository Structure

Devmarketbackendfinal/
├── server.py
├── requirements.txt
└── README.md

The primary backend implementation is contained in "server.py", with dependencies defined in "requirements.txt".

Running Locally

Clone the repository:

git clone <repository-url>
cd Devmarketbackendfinal

Install dependencies:

pip install -r requirements.txt

Configure the required environment variables for the database, authentication, and Cloudinary integration.

Start the development server:

python server.py

Security

Production credentials should never be committed to source control.

Database credentials, authentication secrets, Cloudinary credentials, and other sensitive configuration should be supplied through environment variables.

Project Status

Backend MVP / Active Development

DevMarket Backend is maintained as the server-side component of the DevMarket marketplace.

Related Project

The corresponding DevMarket frontend is maintained separately.