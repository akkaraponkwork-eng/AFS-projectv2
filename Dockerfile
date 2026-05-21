# ใช้ Official Image ของ Playwright (ครอบคลุม Dependencies ทั้งหมดของ Chromium อัตโนมัติ)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# ตั้งค่า Working Directory ใน Container
WORKDIR /app

# คัดลอกไฟล์ requirements.txt และติดตั้ง Library
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกซอร์สโค้ดทั้งหมดลงใน Container
COPY . .

# เปิด Port 10000 (Render มักจะใช้ Port นี้)
EXPOSE 10000

# สั่งรันแอปพลิเคชันด้วย Gunicorn
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:10000", "--timeout", "300", "app:app"]
