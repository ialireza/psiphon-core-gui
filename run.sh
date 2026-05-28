#!/bin/bash

# رنگ‌ها برای خروجی
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 مدیر سایفون${NC}"
echo "========================"

# بررسی وجود پایتون
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}❌ پایتون ۳ نصب نیست. لطفاً نصب کنید:${NC}"
    echo "  sudo dnf install python3  # برای فدورا"
    echo "  sudo apt install python3   # برای اوبونتو/دبیان"
    exit 1
fi

# بررسی وجود محیط مجازی
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 ایجاد محیط مجازی...${NC}"
    python3 -m venv venv
fi

# فعال‌سازی محیط مجازی
echo -e "${GREEN}🔌 فعال‌سازی محیط مجازی...${NC}"
source venv/bin/activate

# نصب وابستگی‌ها
echo -e "${GREEN}📦 نصب وابستگی‌ها...${NC}"
pip install -r requirements.txt

# بررسی وجود فایل باینری
if [ ! -f "psiphon-tunnel-core-x86_64" ]; then
    echo -e "${YELLOW}⚠️  فایل باینری سایفون پیدا نشد!${NC}"
    echo "لطفاً فایل psiphon-tunnel-core-x86_64 رو از"
    echo "https://github.com/Psiphon-Labs/psiphon-tunnel-core-binaries"
    echo "دانلود کنید و در همین پوشه قرار دهید."
    read -p "ادامه می‌دهیم؟ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# اجرای برنامه
echo -e "${GREEN}🎯 اجرای برنامه...${NC}"
python3 psiphon_gui.py

# غیرفعال‌سازی محیط مجازی بعد از بسته شدن برنامه
deactivate