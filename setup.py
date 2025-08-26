#!/usr/bin/env python3
"""
VeriPay Bot - Setup Configuration
"""

from setuptools import setup, find_packages

setup(
    name="veripay-bot",
    version="1.0.0",
    description="Telegram bot for payment verification in Ethiopian restaurants",
    author="VeriPay Team",
    packages=find_packages(),
    install_requires=[
        "aiogram==3.2.0",
        "sqlalchemy==2.0.23",
        "opencv-python==4.8.1.78",
        "pytesseract==0.3.10",
        "Pillow==10.1.0",
        "pyzbar==0.1.9",
        "pyyaml==6.0.1",
        "loguru==0.7.2",
        "requests==2.31.0",
        "numpy==1.24.3",
        "gunicorn==21.2.0",
    ],
    python_requires=">=3.8",
) 