#!/bin/bash

# VeriPay Bot - Supabase Deployment Script
# This script helps you deploy the VeriPay bot to Railway with Supabase database

set -e  # Exit on any error

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if file exists
file_exists() {
    [ -f "$1" ]
}

# Function to check if directory exists
dir_exists() {
    [ -d "$1" ]
}

# Function to validate environment variables
validate_env_vars() {
    print_status "Validating environment variables..."
    
    local missing_vars=()
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        missing_vars+=("TELEGRAM_BOT_TOKEN")
    fi
    
    if [ -z "$DATABASE_URL" ]; then
        missing_vars+=("DATABASE_URL")
    fi
    
    if [ -z "$ADMIN_USER_ID" ]; then
        missing_vars+=("ADMIN_USER_ID")
    fi
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        print_warning "Please set these environment variables before running the script."
        return 1
    fi
    
    print_success "All required environment variables are set"
    return 0
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Python 3 is installed
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        return 1
    fi
    
    # Check Python version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_status "Python version: $python_version"
    
    # Check if pip is installed
    if ! command_exists pip3; then
        print_error "pip3 is not installed. Please install pip."
        return 1
    fi
    
    # Check if git is installed
    if ! command_exists git; then
        print_warning "Git is not installed. Some features may not work."
    fi
    
    print_success "Prerequisites check completed"
    return 0
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if file_exists "requirements_supabase.txt"; then
        pip3 install -r requirements_supabase.txt
        print_success "Dependencies installed successfully"
    else
        print_error "requirements_supabase.txt not found"
        return 1
    fi
}

# Function to setup database
setup_database() {
    print_status "Setting up database..."
    
    if file_exists "setup_supabase.py"; then
        python3 setup_supabase.py
        if [ $? -eq 0 ]; then
            print_success "Database setup completed"
        else
            print_error "Database setup failed"
            return 1
        fi
    else
        print_error "setup_supabase.py not found"
        return 1
    fi
}

# Function to test bot locally
test_bot_locally() {
    print_status "Testing bot locally..."
    
    if file_exists "veripay_supabase_bot.py"; then
        print_warning "Starting bot in test mode (Ctrl+C to stop)..."
        print_status "Bot will run for 30 seconds to test functionality..."
        
        # Start bot in background
        python3 veripay_supabase_bot.py &
        BOT_PID=$!
        
        # Wait for 30 seconds
        sleep 30
        
        # Stop bot
        kill $BOT_PID 2>/dev/null || true
        
        print_success "Local test completed"
    else
        print_error "veripay_supabase_bot.py not found"
        return 1
    fi
}

# Function to prepare for deployment
prepare_deployment() {
    print_status "Preparing for deployment..."
    
    # Check if required files exist
    local required_files=(
        "veripay_supabase_bot.py"
        "requirements_supabase.txt"
        "railway_supabase.json"
        "Procfile_supabase"
        "runtime_supabase.txt"
        "config_supabase.yaml"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if ! file_exists "$file"; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        print_error "Missing required files for deployment:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi
    
    # Rename files for deployment
    if file_exists "Procfile_supabase"; then
        cp Procfile_supabase Procfile
        print_status "Created Procfile for deployment"
    fi
    
    if file_exists "runtime_supabase.txt"; then
        cp runtime_supabase.txt runtime.txt
        print_status "Created runtime.txt for deployment"
    fi
    
    if file_exists "railway_supabase.json"; then
        cp railway_supabase.json railway.json
        print_status "Created railway.json for deployment"
    fi
    
    print_success "Deployment preparation completed"
}

# Function to show deployment instructions
show_deployment_instructions() {
    echo ""
    print_status "🚀 Deployment Instructions"
    echo "================================"
    echo ""
    echo "1. 📋 Prerequisites:"
    echo "   - GitHub account"
    echo "   - Railway account (free tier)"
    echo "   - Supabase account (free tier)"
    echo "   - Telegram bot token"
    echo ""
    echo "2. 🗄️  Supabase Setup:"
    echo "   - Go to https://supabase.com"
    echo "   - Create new project"
    echo "   - Copy database connection string"
    echo "   - Run SQL from SUPABASE_DEPLOYMENT.md"
    echo ""
    echo "3. 🚀 Railway Deployment:"
    echo "   - Go to https://railway.app"
    echo "   - Connect GitHub repository"
    echo "   - Set environment variables:"
    echo "     TELEGRAM_BOT_TOKEN=your_bot_token"
    echo "     DATABASE_URL=your_supabase_url"
    echo "     ADMIN_USER_ID=your_telegram_id"
    echo ""
    echo "4. 🧪 Testing:"
    echo "   - Find your bot on Telegram"
    echo "   - Send /start command"
    echo "   - Test registration and features"
    echo ""
    echo "📖 For detailed instructions, see SUPABASE_DEPLOYMENT.md"
    echo ""
}

# Function to show current status
show_status() {
    echo ""
    print_status "📊 Current Status"
    echo "=================="
    echo ""
    
    # Check environment variables
    if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        echo "✅ TELEGRAM_BOT_TOKEN: Set"
    else
        echo "❌ TELEGRAM_BOT_TOKEN: Not set"
    fi
    
    if [ -n "$DATABASE_URL" ]; then
        echo "✅ DATABASE_URL: Set"
    else
        echo "❌ DATABASE_URL: Not set"
    fi
    
    if [ -n "$ADMIN_USER_ID" ]; then
        echo "✅ ADMIN_USER_ID: Set"
    else
        echo "❌ ADMIN_USER_ID: Not set"
    fi
    
    # Check files
    echo ""
    echo "📁 Required Files:"
    
    local files=(
        "veripay_supabase_bot.py"
        "requirements_supabase.txt"
        "config_supabase.yaml"
        "setup_supabase.py"
    )
    
    for file in "${files[@]}"; do
        if file_exists "$file"; then
            echo "✅ $file"
        else
            echo "❌ $file"
        fi
    done
    
    echo ""
}

# Main function
main() {
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                VeriPay Bot - Supabase Deployment             ║"
    echo "║                                                              ║"
    echo "║  🚀 Automated deployment script                              ║"
    echo "║  🗄️  Supabase PostgreSQL database                            ║"
    echo "║  ☁️  Railway cloud hosting                                    ║"
    echo "║  🤖 Telegram bot integration                                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Parse command line arguments
    case "${1:-help}" in
        "setup")
            print_status "Running setup..."
            check_prerequisites || exit 1
            install_dependencies || exit 1
            validate_env_vars || exit 1
            setup_database || exit 1
            print_success "Setup completed successfully!"
            ;;
        "test")
            print_status "Running local test..."
            validate_env_vars || exit 1
            test_bot_locally || exit 1
            print_success "Local test completed!"
            ;;
        "deploy")
            print_status "Preparing for deployment..."
            check_prerequisites || exit 1
            install_dependencies || exit 1
            validate_env_vars || exit 1
            prepare_deployment || exit 1
            show_deployment_instructions
            print_success "Ready for deployment!"
            ;;
        "status")
            show_status
            ;;
        "help"|*)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  setup   - Install dependencies and setup database"
            echo "  test    - Test bot locally"
            echo "  deploy  - Prepare for cloud deployment"
            echo "  status  - Show current status"
            echo "  help    - Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  TELEGRAM_BOT_TOKEN - Your Telegram bot token"
            echo "  DATABASE_URL       - Supabase database connection string"
            echo "  ADMIN_USER_ID      - Your Telegram user ID"
            echo ""
            show_status
            ;;
    esac
}

# Run main function
main "$@" 