# victor-floppy-db

Django application to manage database of Victor 9000 floppy disks for archival preservation on Archive.org.

## Overview

This Django application provides a comprehensive system for managing metadata about vintage Victor 9000 floppy disks, processing their contents, and uploading them to the Internet Archive for preservation. It includes support for:

- Metadata management (titles, creators, subjects, languages, collections)
- Disk image processing (A2R/FLUX flux images, IMG files)
- File content archiving (ZIP archives with MD5 checksums)
- Photo management (front/back disk images)
- Internet Archive integration
- Web-based interface for data entry and management

## Features

- **Rich Metadata**: Track comprehensive information about each disk
- **A2R/FLUX Support**: Parse Apple II flux image metadata
- **Batch Processing**: Scripts for bulk import and update operations
- **Search & Filter**: Find disks by title, identifier, status
- **Archive Integration**: Direct upload to Internet Archive
- **Audit Logging**: Track all script operations

## Requirements

- Python 3.8+
- PostgreSQL 12+
- Django 4.2.7

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/victor-floppy-db.git
cd victor-floppy-db
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note for macOS users**: If you want to use macOS Finder tag features, uncomment the `osxmetadata` line in `requirements.txt` and reinstall:

```bash
# Uncomment osxmetadata in requirements.txt, then:
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

Create a PostgreSQL database and user:

```sql
CREATE DATABASE victordisk;
CREATE USER victordisk_user WITH PASSWORD 'your_password';
ALTER ROLE victordisk_user SET client_encoding TO 'utf8';
ALTER ROLE victordisk_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE victordisk_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE victordisk TO victordisk_user;
```

### 5. Configure Environment Variables

Copy the example environment file and edit it with your settings:

```bash
cp .env.example .env
```

Edit `.env` and configure:

```bash
# Generate a new SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Update `.env` with your values:

```
SECRET_KEY=your-generated-secret-key
DEBUG=True  # Set to False in production!
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=victordisk
DB_USER=victordisk_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DISK_MUSTERING_DIR=/path/to/your/disk/files
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create a Superuser

```bash
python manage.py createsuperuser
```

### 8. Collect Static Files

```bash
python manage.py collectstatic
```

### 9. Run the Development Server

```bash
python manage.py runserver
```

Visit http://localhost:8000 to access the application.

## Usage

### Web Interface

- **Admin Interface**: http://localhost:8000/admin - Full CRUD operations
- **Main Interface**: http://localhost:8000 - Browse, search, and manage entries
- **Search**: Use the search bar to find disks by title or identifier
- **Filters**:
  - `?needswork=true` - Show entries needing manual review
  - `?nextupload=true` - Show entries ready for upload
  - `?dateorder=true` - Order by modification date

### Scripts

#### Create New Entries from Filesystem

```bash
cd scripts
python create_records_from_diskmustering.py /path/to/disk/mustering/area
```

This script scans for folders tagged "Yellow" in macOS Finder (if osxmetadata is available) and creates database entries.

#### Update Existing Entries

```bash
cd scripts
python update_records_from_diskmustering.py
```

Updates entries with current filesystem information (ZIP contents, photos, flux files).

#### Upload to Internet Archive

```bash
cd scripts
python upload_to_iarchive.py
```

Uploads entries marked as `readyToUpload=True` to the Internet Archive.

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python manage.py test

# Run with coverage
pip install pytest pytest-django pytest-cov
pytest --cov=floppies --cov-report=html

# Run utility tests
python -m pytest scripts/test_utils.py
```

## Project Structure

```
victor-floppy-db/
├── victordisk/          # Django project settings
│   ├── settings.py      # Main configuration
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI configuration
├── floppies/            # Main Django app
│   ├── models.py        # Database models
│   ├── views.py         # View handlers
│   ├── forms.py         # Form definitions
│   ├── admin.py         # Admin configuration
│   ├── tests.py         # Test suite
│   ├── templates/       # HTML templates
│   └── static/          # CSS, JavaScript
├── scripts/             # Utility scripts
│   ├── disk_mustering.py          # Core library
│   ├── create_records_from_diskmustering.py
│   ├── update_records_from_diskmustering.py
│   ├── upload_to_iarchive.py
│   ├── a2r_reader.py              # A2R file parser
│   └── zip_contents.py            # ZIP processing
├── requirements.txt     # Python dependencies
└── .env.example        # Environment template
```

## Data Model

### Key Models

- **Entry**: Main disk record with metadata
- **Creator, Contributor**: People involved
- **Subject, Language, ArchCollection**: Categorization
- **ZipArchive, ZipContent**: File contents and metadata
- **FluxFile, InfoChunk, MetaChunk**: A2R flux image data
- **PhotoImage**: Disk photographs
- **ScriptRun**: Audit log

## Security Considerations

### Production Deployment

Before deploying to production:

1. **Set DEBUG=False** in `.env`
2. **Use a strong SECRET_KEY** (never commit to version control)
3. **Configure ALLOWED_HOSTS** with your domain(s)
4. **Use HTTPS** (configure with reverse proxy like nginx)
5. **Set up proper file upload restrictions** for CKEditor
6. **Enable PostgreSQL SSL** connections
7. **Regular backups** of database and media files
8. **Keep dependencies updated** (run `pip list --outdated` regularly)

### Authentication

The CKEditor upload endpoint is configured to require authentication. Ensure users are properly authenticated before accessing file upload features.

## Development

### Code Style

This project follows PEP 8 style guidelines. Format code with:

```bash
black .
isort .
flake8 .
```

### Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Troubleshooting

### Common Issues

**Database connection errors**:
- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `.env`
- Ensure database exists: `psql -l`

**Import errors in scripts**:
- Set `DJANGO_PROJECT_PATH` environment variable
- Or run scripts from the correct directory

**macOS Finder tag features not working**:
- Install osxmetadata: `pip install osxmetadata`
- This feature only works on macOS

**Static files not loading**:
- Run `python manage.py collectstatic`
- Check `STATIC_ROOT` and `STATIC_URL` settings

## License

[Add your license here]

## Credits

Created for the preservation of Victor 9000 computer software and documentation.

## Support

For issues or questions, please open an issue on GitHub.
