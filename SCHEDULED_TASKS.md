# Scheduled Tasks Configuration

This document describes the automated tasks configured for the trading system via cron jobs.

## Cron Jobs

The following automated tasks are scheduled in the system:

### Scanner
- **Frequency:** Every 30 minutes (`*/30 * * * *`)
- **Command:** `python scanner.py --notify`
- **Purpose:** Scan news feeds for trading opportunities and send notifications
- **Log:** `logs/scanner.log`

### Position Monitor
- **Frequency:** Every 15 minutes (`*/15 * * * *`)
- **Command:** `python alerts/position_monitor.py`
- **Purpose:** Check open positions and alert on significant price movements
- **Log:** `logs/positions.log`

### Dashboard Update
- **Frequency:** Hourly (`0 * * * *`)
- **Command:** `python dashboard.py`
- **Purpose:** Refresh portfolio statistics and performance metrics
- **Log:** `logs/dashboard.log`

### Auto Monitor
- **Frequency:** Hourly (`0 * * * *`)
- **Command:** `python auto_monitor.py`
- **Purpose:** Check news and prices automatically
- **Log:** `logs/auto_monitor.log`

## Management

### To view current cron jobs:
```bash
crontab -l
```

### To modify the schedule:
Edit the `setup_cron.py` script and re-run it, or modify the crontab directly:
```bash
crontab -e
```

### To check logs:
```bash
# View recent scanner logs
tail -20 logs/scanner.log

# View recent position monitor logs
tail -20 logs/positions.log

# View recent dashboard logs
tail -20 logs/dashboard.log

# View recent auto monitor logs
tail -20 logs/auto_monitor.log
```

## Troubleshooting

If cron jobs are not running:
1. Check that the Python virtual environment path is correct in the cron jobs
2. Ensure the working directory exists and has proper permissions
3. Check system logs: `grep CRON /var/log/syslog`
4. Verify the cron daemon is running: `systemctl status cron`

## Notes

- All cron jobs run in the `/home/rafa/clawd/trading-system` directory
- All output is redirected to the respective log files
- Errors are also captured in the log files
- The Python virtual environment is explicitly referenced to ensure proper dependencies