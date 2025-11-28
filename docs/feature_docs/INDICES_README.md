# NSE Indices Management System

A comprehensive, modular system for managing NSE (National Stock Exchange) indices data with database storage, CSV parsing, and API access for analysis and reporting.

## Features

- **Modular Architecture**: Clean separation of concerns with dedicated modules for parsing, database operations, importing, and API access
- **Database Storage**: MySQL-based storage with proper schema design, constraints, and indexing
- **CSV Processing**: Robust parsing of NSE market-wide index files with data validation and cleaning
- **Import Management**: Batch import capabilities with duplicate detection and error tracking
- **API Interface**: Clean API for other system components to access indices and constituents data
- **CLI Tools**: Command-line interface for managing imports and querying data
- **Analytics**: Built-in support for performance analysis, market breadth, and sectoral insights

## Architecture

### Database Schema
- `nse_indices`: Index metadata (code, name, category, sector)
- `nse_index_data`: Daily index values (OHLC, volume, performance metrics)
- `nse_index_constituents`: Index constituents with weights and performance
- `index_import_log`: Import tracking with status and error logging

### Components

```
indices_manager/
├── __init__.py          # Package initialization
├── models.py           # Data models and validation
├── database.py         # Database connection and utilities  
├── parser.py           # CSV parsing and validation
├── importer.py         # Data import functionality
└── api.py              # API interface for data access

sql/
└── create_indices_tables.sql  # Database schema

indices_cli.py           # Command-line interface
test_indices_system.py   # Integration tests
```

## Quick Start

### 1. System Setup

```bash
# Ensure database is configured (uses existing reporting_adv_decl configuration)
# No additional setup required if main system is already configured

# Test the system
python test_indices_system.py
```

### 2. Import Data

```bash
# Import a single CSV file
python indices_cli.py import file "path/to/MW-NIFTY-50-15-Nov-2025.csv"

# Import all CSV files from a directory
python indices_cli.py import dir "indices/"

# Force re-import of already processed files
python indices_cli.py import dir "indices/" --force
```

### 3. Query Data

```bash
# List all available indices
python indices_cli.py list indices

# List sectoral indices only
python indices_cli.py list indices --category SECTORAL

# Show latest data for NIFTY-50
python indices_cli.py show NIFTY-50

# Show NIFTY-50 constituents with top gainers/losers
python indices_cli.py show NIFTY-50 --constituents

# Check system status
python indices_cli.py status
```

## Programming API

### Basic Usage

```python
from indices_manager import indices_api, IndicesImporter

# Get all indices
indices = indices_api.get_all_indices()

# Get sectoral indices only
sectoral_indices = indices_api.get_all_indices(category='SECTORAL')

# Get latest NIFTY-50 data
latest_data = indices_api.get_latest_index_data('NIFTY-50')

# Get NIFTY-50 constituents
constituents_df = indices_api.get_index_constituents('NIFTY-50')

# Get historical index data
historical_df = indices_api.get_index_data('NIFTY-50', limit=30)
```

### Import Data Programmatically

```python
from indices_manager import IndicesImporter

# Initialize importer
importer = IndicesImporter()

# Import single file
success = importer.import_csv_file("MW-NIFTY-50-15-Nov-2025.csv")

# Import directory
results = importer.import_directory("indices/", skip_duplicates=True)
```

### Analytics

```python
# Get index performance over different periods
performance = indices_api.get_index_performance('NIFTY-50', periods=[1, 5, 30, 90])

# Get market breadth (advance/decline ratio)
breadth = indices_api.get_market_breadth('NIFTY-50')

# Get sector performance summary
sector_performance = indices_api.get_sector_performance()

# Get top performers in an index
top_gainers = indices_api.get_top_performers('NIFTY-50', by='change_percent', top_n=10)
```

## CSV File Format

The system expects NSE market-wide index CSV files with this structure:

```
Filename format: MW-{INDEX_CODE}-{DD-MMM-YYYY}.csv
Example: MW-NIFTY-50-15-Nov-2025.csv

Content:
- First row: Index data (name, date, OHLC values, volume, etc.)
- Following rows: Constituent stocks data
```

### Sample CSV Structure

```csv
Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change (%),Volume,Turnover (Rs. Cr.),...
NIFTY 50,15-Nov-2025,24800.50,24950.75,24750.25,24900.30,99.80,0.40,1500000000,85000.50,...

Symbol,Series,Open Price,High Price,Low Price,LTP,Change,% Change,Volume,Value (Rs. Cr.),...
RELIANCE,EQ,2650.00,2680.50,2640.00,2675.25,25.25,0.95,12500000,3342.50,...
TCS,EQ,3950.00,3980.00,3930.00,3965.75,15.75,0.40,8750000,3471.03,...
...
```

## Error Handling

The system includes comprehensive error handling:

- **Validation Errors**: Invalid CSV structure, missing required fields
- **Database Errors**: Connection issues, constraint violations
- **Import Errors**: File processing failures, duplicate detection
- **API Errors**: Invalid parameters, data not found

All errors are logged with detailed context for troubleshooting.

## Integration with Main System

The indices management system integrates seamlessly with the main stock screener:

1. **Database**: Uses the same MySQL connection as `reporting_adv_decl.py`
2. **Logging**: Consistent with main system logging patterns
3. **Configuration**: Leverages existing environment variables and `.env` files
4. **API Design**: Follows patterns established in the main codebase

## Predefined Indices

The system comes with predefined mappings for 24 major NSE indices:

**Main Indices:**
- NIFTY-50, NIFTY-NEXT-50, NIFTY-MIDCAP-SELECT

**Sectoral Indices:**
- Banking: NIFTY-BANK, NIFTY-PRIVATE-BANK, NIFTY-PSU-BANK
- Financial Services: NIFTY-FINANCIAL-SERVICES, NIFTY-FINANCIAL-SERVICES-25_50
- Technology: NIFTY-IT, NIFTY-MIDSMALL-IT-&-TELECOM
- Healthcare: NIFTY-HEALTHCARE-INDEX, NIFTY-MIDSMALL-HEALTHCARE, NIFTY500-HEALTHCARE
- Consumer: NIFTY-FMCG, NIFTY-CONSUMER-DURABLES
- Industrial: NIFTY-AUTO, NIFTY-CHEMICALS, NIFTY-METAL, NIFTY-OIL-&-GAS
- Others: NIFTY-PHARMA, NIFTY-REALTY, NIFTY-MEDIA

## Monitoring and Maintenance

### Import Status Monitoring

```python
# Check recent import status
status_df = indices_api.get_import_status(days=30)

# Get data availability summary
availability_df = indices_api.get_data_availability()
```

### Database Maintenance

```sql
-- Check data completeness
SELECT index_code, COUNT(*) as data_points, 
       MIN(data_date) as earliest, MAX(data_date) as latest
FROM nse_indices i
JOIN nse_index_data d ON i.id = d.index_id
GROUP BY i.index_code
ORDER BY data_points DESC;

-- Check failed imports
SELECT filename, error_message, created_at
FROM index_import_log 
WHERE status = 'FAILED'
ORDER BY created_at DESC;
```

## Future Enhancements

1. **Real-time Updates**: WebSocket integration for live index updates
2. **Advanced Analytics**: Technical indicators, correlation analysis
3. **Data Validation**: Cross-verification with external data sources
4. **Performance Optimization**: Caching layer for frequently accessed data
5. **Web Interface**: Dashboard for visual data exploration
6. **Alerts System**: Notifications for significant market movements

## Contributing

The system is designed for extensibility. Key extension points:

1. **Custom Parsers**: Implement new parsers for different file formats
2. **Analytics Modules**: Add new analytical functions to the API
3. **Data Sources**: Integrate additional data providers
4. **Export Formats**: Add support for different output formats

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure MySQL is running and credentials are correct
2. **CSV Parsing**: Check file format matches expected NSE structure
3. **Import Failures**: Review error logs in `index_import_log` table
4. **Missing Data**: Verify files are being processed and not skipped as duplicates

### Debug Mode

```bash
# Run with verbose logging
python indices_cli.py --verbose [command]

# Run integration tests for diagnosis
python test_indices_system.py
```

## License

Part of the Stock Screener project. See main project documentation for licensing terms.