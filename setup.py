#!/usr/bin/env python3
"""
VeriPay Setup Script
"""
import os
import sys
import subprocess
import yaml
from pathlib import Path
import getpass


def print_banner():
    """Print VeriPay setup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                        VeriPay Setup                        ║
║                                                              ║
║  Telegram-based Payment Verification System for Ethiopia    ║
║                                                              ║
║  🎯 Eliminate fake payment screenshots                      ║
║  🔍 AI-powered fraud detection                              ║
║  📊 Automated audit reconciliation                          ║
║  💼 Streamlined Telegram workflow                           ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def check_dependencies():
    """Check if required system dependencies are installed"""
    print("\n🔍 Checking system dependencies...")
    
    dependencies = [
        ('tesseract', 'tesseract --version'),
        ('docker', 'docker --version'),
        ('docker-compose', 'docker-compose --version'),
    ]
    
    missing = []
    for name, command in dependencies:
        try:
            subprocess.run(command.split(), capture_output=True, check=True)
            print(f"✅ {name} found")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {name} not found")
            missing.append(name)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("Please install the missing dependencies and run setup again.")
        return False
    
    return True


def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        'uploads',
        'logs',
        'reports',
        'models',
        'backups',
        'tests',
        'nginx',
        'monitoring'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created {directory}/")


def setup_virtual_environment():
    """Setup Python virtual environment"""
    print("\n🐍 Setting up virtual environment...")
    
    if not Path('venv').exists():
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError:
            print("❌ Failed to create virtual environment")
            return False
    else:
        print("✅ Virtual environment already exists")
    
    return True


def install_python_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    
    # Determine pip command based on OS
    if os.name == 'nt':  # Windows
        pip_cmd = 'venv\\Scripts\\pip'
    else:  # Unix/Linux/macOS
        pip_cmd = 'venv/bin/pip'
    
    try:
        subprocess.run([pip_cmd, 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Python dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python dependencies")
        return False


def configure_environment():
    """Configure environment variables"""
    print("\n⚙️  Configuring environment...")
    
    # Check if .env file exists
    if Path('.env').exists():
        print("✅ .env file already exists")
        return True
    
    print("Please provide the following configuration details:")
    
    config = {}
    
    # Telegram Bot Tokens
    print("\n🤖 Telegram Bot Configuration:")
    config['WAITER_BOT_TOKEN'] = input("Waiter Bot Token: ").strip()
    config['ADMIN_BOT_TOKEN'] = input("Admin Bot Token: ").strip()
    
    # Database Configuration
    print("\n🗄️  Database Configuration:")
    config['DATABASE_URL'] = input("Database URL (default: postgresql://veripay_user:veripay_password@localhost:5432/veripay): ").strip()
    if not config['DATABASE_URL']:
        config['DATABASE_URL'] = "postgresql://veripay_user:veripay_password@localhost:5432/veripay"
    
    # Admin Configuration
    print("\n👤 Admin Configuration:")
    config['ADMIN_TELEGRAM_ID'] = input("Admin Telegram User ID: ").strip()
    
    # Security Configuration
    print("\n🔒 Security Configuration:")
    config['ENCRYPTION_KEY'] = getpass.getpass("Encryption Key (will be hidden): ").strip()
    
    # Write .env file
    with open('.env', 'w') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    print("✅ Environment configuration saved to .env")
    return True


def setup_database():
    """Setup database"""
    print("\n🗄️  Setting up database...")
    
    try:
        # Create database tables
        subprocess.run([sys.executable, '-c', 'from database.models import Base, engine; Base.metadata.create_all(engine)'], check=True)
        print("✅ Database tables created")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create database tables")
        return False


def create_sample_data():
    """Create sample data for testing"""
    print("\n📊 Creating sample data...")
    
    try:
        # Create sample restaurant and admin
        sample_script = """
from database.operations import DatabaseManager, RestaurantOperations, AdminOperations, WaiterOperations
from database.models import BankType

# Get database session
db_manager = DatabaseManager()
session = db_manager.get_session()

# Create sample restaurant
restaurant = RestaurantOperations.create_restaurant(
    session=session,
    name="Sample Restaurant",
    address="Addis Ababa, Ethiopia",
    phone="+251911234567",
    email="restaurant@example.com",
    admin_telegram_id="YOUR_ADMIN_TELEGRAM_ID"
)

# Create sample admin
admin = AdminOperations.create_admin(
    session=session,
    telegram_id="YOUR_ADMIN_TELEGRAM_ID",
    name="Sample Admin",
    email="admin@example.com",
    is_super_admin=True
)

# Create sample waiter
waiter = WaiterOperations.create_waiter(
    session=session,
    telegram_id="YOUR_WAITER_TELEGRAM_ID",
    name="Sample Waiter",
    phone="+251922345678",
    restaurant_id=restaurant.id
)

print("✅ Sample data created successfully!")
        """
        
        # Replace placeholder with actual admin ID
        with open('.env', 'r') as f:
            env_content = f.read()
        
        admin_id = None
        for line in env_content.split('\n'):
            if line.startswith('ADMIN_TELEGRAM_ID='):
                admin_id = line.split('=')[1]
                break
        
        if admin_id:
            sample_script = sample_script.replace('YOUR_ADMIN_TELEGRAM_ID', admin_id)
            sample_script = sample_script.replace('YOUR_WAITER_TELEGRAM_ID', input("Sample Waiter Telegram ID: ").strip())
        
        # Execute sample data creation
        subprocess.run([sys.executable, '-c', sample_script], check=True)
        print("✅ Sample data created")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to create sample data")
        return False


def setup_logging():
    """Setup logging configuration"""
    print("\n📝 Setting up logging...")
    
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    # Create log files
    log_files = ['veripay.log', 'waiter_bot.log', 'admin_bot.log']
    for log_file in log_files:
        log_path = Path('logs') / log_file
        if not log_path.exists():
            log_path.touch()
    
    print("✅ Logging setup complete")


def run_tests():
    """Run basic tests"""
    print("\n🧪 Running basic tests...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-v'], check=True)
        print("✅ All tests passed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Some tests failed")
        return False


def print_next_steps():
    """Print next steps for the user"""
    next_steps = """
🎉 VeriPay setup completed successfully!

📋 Next Steps:

1. 🤖 Start the bots:
   • Waiter Bot: python bots/waiter_bot.py
   • Admin Bot: python bots/admin_bot.py

2. 🐳 Or use Docker:
   • docker-compose up -d

3. 📱 Configure your Telegram bots:
   • Set webhook URLs if using webhooks
   • Test bot functionality

4. 🗄️  Database management:
   • Monitor database performance
   • Set up regular backups

5. 📊 Monitoring:
   • Check logs in logs/ directory
   • Monitor system performance
   • Set up alerts

🔗 Useful Commands:
• View logs: tail -f logs/veripay.log
• Database backup: pg_dump veripay > backup.sql
• Restart services: docker-compose restart

📞 Support:
• Documentation: README.md
• Issues: Create GitHub issue
• Contact: support@veripay.et

Happy verifying! 💳✅
    """
    print(next_steps)


def main():
    """Main setup function"""
    print_banner()
    
    # Check Python version
    check_python_version()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Setup virtual environment
    if not setup_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_python_dependencies():
        sys.exit(1)
    
    # Configure environment
    if not configure_environment():
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        sys.exit(1)
    
    # Create sample data
    create_sample = input("\n📊 Create sample data for testing? (y/n): ").strip().lower()
    if create_sample == 'y':
        create_sample_data()
    
    # Setup logging
    setup_logging()
    
    # Run tests
    run_tests_choice = input("\n🧪 Run basic tests? (y/n): ").strip().lower()
    if run_tests_choice == 'y':
        run_tests()
    
    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    main() 