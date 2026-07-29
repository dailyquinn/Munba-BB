# Quote Cleanup System

This document describes the automatic quote cleanup feature implemented in the GDS-BB application.

## Overview

The application now includes an automatic cleanup system that removes quote entries older than 7 days from the database. This prevents the quotes table from growing indefinitely and helps maintain optimal database performance.

## Implementation Details

### Database Schema
Quotes are stored in the `quotes` table with the following structure:
- `code` (TEXT PRIMARY KEY): 6-character hex identifier
- `content` (TEXT): The original quote content
- `created_at` (INTEGER): Unix timestamp when the quote was created

### Automatic Cleanup

#### Daily Schedule
- **Trigger**: Every day at **midnight UTC**
- **Action**: Deletes all quotes where `created_at` is older than 7 days
- **Logging**: Reports the number of quotes deleted (or "No old quotes to delete")

#### Background Thread
The cleanup runs in a daemon background thread alongside the existing market price refresh system:
- `daily_quote_cleanup()` - Calculates time until next midnight UTC and sleeps until then
- `cleanup_old_quotes()` - Performs the actual database cleanup operation

### Manual Cleanup Endpoint

For testing and administrative purposes, there's a manual endpoint:

```http
POST /api/quotes/cleanup
```

**Response:**
```json
{
  "success": true,
  "message": "Quote cleanup completed successfully"
}
```

### Logging

The system provides detailed logging with timestamps:
- `[Quote Cleanup] Next cleanup in X.X hours at YYYY-MM-DD HH:MM UTC`
- `[Quote Cleanup] Deleted N quotes older than 7 days`
- `[Quote Cleanup] No old quotes to delete`
- `[Quote Cleanup] Daily cleanup completed at YYYY-MM-DD HH:MM:SS UTC`

## Error Handling

The system includes comprehensive error handling:
- Database connection errors are caught and logged
- Failed cleanup attempts retry after 1 hour
- SQLite operational errors are handled gracefully
- The system continues running even if individual cleanup operations fail

## Benefits

1. **Storage Efficiency**: Prevents unlimited database growth
2. **Performance**: Keeps the quotes table at a manageable size
3. **Privacy**: Automatically removes old user data
4. **Maintenance-Free**: Runs automatically without manual intervention
5. **Configurable**: Easy to modify the 7-day retention period if needed

## Configuration

To modify the retention period, change the calculation in `cleanup_old_quotes()`:
```python
# Current: 7 days
seven_days_ago = int(time.time()) - (7 * 24 * 60 * 60)

# Example: 30 days
thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
```

## Monitoring

Check the Docker container logs to monitor cleanup operations:
```bash
docker-compose logs | grep "Quote Cleanup"
```

The next scheduled cleanup time is displayed on application startup.