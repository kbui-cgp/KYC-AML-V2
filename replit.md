# CIF Workflow Management System

## Overview

This is a French financial advisory workflow management system designed for Conseiller en Gestion de Patrimoine (CGP - Wealth Management Advisors). The application manages the complete client onboarding process from initial contact to document generation, following French financial regulations (MiFID II compliance). It handles DER (Document d'Entrée en Relation), KYC document collection, investor profile questionnaires, and automated generation of regulatory documents like adequacy reports and mission letters.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme integration
- **Styling**: Custom CSS with CSS variables for consistent theming and responsive design
- **JavaScript**: Vanilla JavaScript for interactive questionnaire with real-time score calculation
- **UI Framework**: Bootstrap 5 with Font Awesome icons for professional financial interface
- **Responsive Design**: Mobile-first approach with collapsible navigation and responsive tables

### Backend Architecture
- **Web Framework**: Flask with SQLAlchemy ORM for rapid development and database abstraction
- **Database Models**: Enum-based workflow status tracking and comprehensive client data modeling
- **File Handling**: Secure file upload system with type validation and size limits (16MB max)
- **Document Generation**: Python-docx integration for automated regulatory document creation
- **Session Management**: Flask sessions with configurable secret keys
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies

### Data Storage Solutions
- **Primary Database**: SQLite for development with PostgreSQL-ready configuration
- **File Storage**: Local filesystem with organized directory structure (uploads/, generated_documents/)
- **Connection Pooling**: SQLAlchemy with pool recycling and pre-ping for connection reliability
- **Schema Management**: Declarative base with automatic table creation on startup

### Authentication and Authorization
- **Session-based Authentication**: Flask sessions with secure secret key management
- **File Access Control**: Secure filename handling with werkzeug utilities
- **Environment-based Configuration**: Production-ready configuration management

### Workflow Management
- **Status Tracking**: Enum-based workflow states (CREATED → DER_COMPLETED → DOCUMENTS_UPLOADED → QUESTIONNAIRE_COMPLETED → DOCUMENTS_GENERATED → COMPLETED)
- **Progressive Disclosure**: Step-by-step client onboarding process
- **Document Lifecycle**: Automated document generation based on workflow completion
- **Validation Rules**: Multi-stage validation for financial data and document requirements

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web application framework with SQLAlchemy integration
- **python-docx**: Document generation for regulatory reports and mission letters
- **Werkzeug**: Secure file handling and HTTP utilities
- **Bootstrap 5**: Frontend framework with dark theme support
- **Font Awesome**: Icon library for professional UI elements

### Database and ORM
- **SQLAlchemy**: Database ORM with enum support for workflow states
- **SQLite**: Development database with PostgreSQL migration path

### Document Processing
- **DOCX Templates**: Template-based document generation for French regulatory compliance
- **File Upload Security**: Type validation and size limits for KYC documents

### Frontend Assets
- **CDN Dependencies**: Bootstrap CSS/JS and Font Awesome from reliable CDNs
- **Custom Styling**: CSS variables for consistent theming across the application

### Deployment and Configuration
- **Environment Variables**: Database URL, session secrets, and configuration management
- **Static File Serving**: Flask static file handling for CSS, JavaScript, and generated documents
- **Development Server**: Built-in Flask development server with debug mode