#!/usr/bin/env python3
"""
Setup cron jobs for the trading system to run automated scans
"""
import subprocess
import sys
import os
from pathlib import Path

def setup_cron_jobs():
    """Setup cron jobs for the trading system"""
    
    # Get the absolute path to the trading system directory
    trading_dir = Path(__file__).parent
    venv_python = str(trading_dir / "venv" / "bin" / "python")
    
    # Define the cron jobs
    cron_jobs = [
        # Run scanner every 30 minutes to check for opportunities
        f"*/30 * * * * cd {trading_dir} && {venv_python} scanner.py --notify >> logs/scanner.log 2>&1",
        
        # Run position monitor every 15 minutes to check open positions
        f"*/15 * * * * cd {trading_dir} && {venv_python} alerts/position_monitor.py >> logs/positions.log 2>&1",
        
        # Run dashboard update every hour to refresh stats
        f"0 * * * * cd {trading_dir} && {venv_python} dashboard.py >> logs/dashboard.log 2>&1",
        
        # Run auto monitor every hour to check news and prices
        f"0 * * * * cd {trading_dir} && {venv_python} auto_monitor.py >> logs/auto_monitor.log 2>&1"
    ]
    
    # Read current crontab
    try:
        current_crontab = subprocess.run(['crontab', '-l'], capture_output=True, text=True, check=False)
        if current_crontab.returncode == 0:
            current_lines = current_crontab.stdout.strip().split('\n')
        else:
            current_lines = []
    except Exception:
        current_lines = []
    
    # Filter out any existing trading system cron jobs
    filtered_lines = []
    for line in current_lines:
        if line.strip() and '# Trading System' not in line:
            filtered_lines.append(line)
    
    # Add our new cron jobs
    filtered_lines.extend(cron_jobs)
    
    # Write the new crontab
    new_crontab = '\n'.join(filtered_lines) + '\n'
    
    try:
        # Write to a temporary file and install
        with open('/tmp/trading_crontab', 'w') as f:
            f.write(new_crontab)
        
        # Install the crontab
        result = subprocess.run(['crontab', '/tmp/trading_crontab'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error installing crontab: {result.stderr}")
            return False
            
        print("Cron jobs successfully installed!")
        
        # Print the installed crontab
        print("\nCurrent trading system cron jobs:")
        for job in cron_jobs:
            print(f"  {job}")
            
        return True
        
    except Exception as e:
        print(f"Error setting up cron jobs: {e}")
        return False

def main():
    print("Setting up cron jobs for trading system...")
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    success = setup_cron_jobs()
    
    if success:
        print("\n✅ Cron jobs have been set up successfully!")
        print("The scanner will now run automatically every 30 minutes")
        print("along with other monitoring tasks at appropriate intervals.")
    else:
        print("\n❌ Failed to set up cron jobs")
        sys.exit(1)

if __name__ == "__main__":
    main()