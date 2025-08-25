#!/bin/bash

# VeriPay Bot Deployment Script
# This script deploys the VeriPay bot with proper logging and monitoring

set -e

# Configuration
BOT_NAME="veripay_bot"
BOT_DIR="/Users/macbook/veripay"
BOT_SCRIPT="lean_veripay_bot.py"
LOG_DIR="$BOT_DIR/logs"
PID_FILE="$BOT_DIR/veripay_bot.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if bot is running
is_bot_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    return 1
}

# Function to start the bot
start_bot() {
    print_status "Starting VeriPay Bot deployment..."
    
    # Check if bot is already running
    if is_bot_running; then
        print_warning "Bot is already running!"
        return 1
    fi
    
    # Create log directory if it doesn't exist
    mkdir -p "$LOG_DIR"
    
    # Change to bot directory
    cd "$BOT_DIR"
    
    # Check if Python script exists
    if [ ! -f "$BOT_SCRIPT" ]; then
        print_error "Bot script not found: $BOT_SCRIPT"
        return 1
    fi
    
    # Check if requirements are installed
    print_status "Checking dependencies..."
    if ! python3 -c "import aiogram, sqlalchemy, cv2, PIL, pyzbar, yaml" 2>/dev/null; then
        print_warning "Some dependencies might be missing. Installing..."
        pip3 install -r lean_requirements.txt
    fi
    
    # Start the bot with logging
    print_status "Starting VeriPay Bot..."
    nohup python3 "$BOT_SCRIPT" > "$LOG_DIR/bot.log" 2>&1 &
    local pid=$!
    
    # Save PID
    echo "$pid" > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 2
    if ps -p "$pid" > /dev/null 2>&1; then
        print_success "VeriPay Bot started successfully! (PID: $pid)"
        print_status "Log file: $LOG_DIR/bot.log"
        print_status "PID file: $PID_FILE"
        return 0
    else
        print_error "Failed to start bot!"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop the bot
stop_bot() {
    print_status "Stopping VeriPay Bot..."
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid"
            rm -f "$PID_FILE"
            print_success "Bot stopped successfully!"
        else
            print_warning "Bot was not running."
            rm -f "$PID_FILE"
        fi
    else
        print_warning "No PID file found. Bot might not be running."
    fi
}

# Function to restart the bot
restart_bot() {
    print_status "Restarting VeriPay Bot..."
    stop_bot
    sleep 2
    start_bot
}

# Function to show bot status
show_status() {
    print_status "VeriPay Bot Status:"
    echo "========================"
    
    if is_bot_running; then
        local pid=$(cat "$PID_FILE")
        print_success "✅ Bot is RUNNING (PID: $pid)"
        echo "📁 Log file: $LOG_DIR/bot.log"
        echo "📁 PID file: $PID_FILE"
        
        # Show recent logs
        if [ -f "$LOG_DIR/bot.log" ]; then
            echo ""
            print_status "Recent logs (last 10 lines):"
            echo "------------------------"
            tail -n 10 "$LOG_DIR/bot.log"
        fi
    else
        print_error "❌ Bot is NOT RUNNING"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_DIR/bot.log" ]; then
        print_status "Showing bot logs:"
        echo "=================="
        tail -f "$LOG_DIR/bot.log"
    else
        print_error "No log file found!"
    fi
}

# Function to show help
show_help() {
    echo "VeriPay Bot Deployment Script"
    echo "============================"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     - Start the VeriPay bot"
    echo "  stop      - Stop the VeriPay bot"
    echo "  restart   - Restart the VeriPay bot"
    echo "  status    - Show bot status and recent logs"
    echo "  logs      - Show live logs"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start    # Start the bot"
    echo "  $0 status   # Check if bot is running"
    echo "  $0 logs     # View live logs"
}

# Main script logic
case "${1:-help}" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 