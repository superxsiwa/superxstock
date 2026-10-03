# 🚀 Master Development Roadmap: SuperX Stock

เอกสารนี้รวบรวมแผนงานทั้งหมด (Master Plan) ในการยกระดับโปรเจกต์ SuperX Stock จากสถานะ **MVP (Minimum Viable Product)** ไปสู่ระบบที่พร้อมสำหรับ **Production** โดยแบ่งออกเป็นเฟสต่างๆ ดังนี้:

---

## ✅ Phase 1: Database Persistence (Completed)
**สถานะ:** ทำเสร็จแล้ว
**เป้าหมาย:** เลิกใช้หน่วยความจำชั่วคราว (In-Memory) และนำฐานข้อมูลจริงมาใช้
*   [x] เชื่อมต่อ **TimescaleDB (PostgreSQL)** เข้ากับระบบ
*   [x] สร้าง Schema ฐานข้อมูล (`users`, `portfolios`, `positions`, `transactions`) ด้วย SQLAlchemy
*   [x] แก้ไข Logic การซื้อ/ขาย (`services.py`) ให้บันทึกข้อมูลทุกอย่างลง Database เพื่อไม่ให้ข้อมูลหายเมื่อเซิร์ฟเวอร์รีสตาร์ท

## ✅ Phase 2: Market Data Integration (Completed)
**สถานะ:** ทำเสร็จแล้ว
**เป้าหมาย:** เปลี่ยนจากการสุ่มกราฟ (Mock Data) เป็นข้อมูลจริงจากตลาดหุ้น
*   [x] เชื่อมต่อกับ **Yahoo Finance API** (`yfinance`) 
*   [x] ดึงข้อมูล OHLCV (Open, High, Low, Close, Volume) ของหุ้นไทย (เช่น AOT.BK, PTT.BK) ย้อนหลัง 90 วัน
*   [x] ส่งข้อมูลจริงเข้าสู่ระบบคำนวณ Indicator (RSI, MACD)

## ✅ Phase 3: Background Jobs & Caching (Completed)
**สถานะ:** ทำเสร็จแล้ว
**เป้าหมาย:** แยกงานหนักออกไปทำเบื้องหลัง เพื่อไม่ให้ API ค้าง (Timeout)
*   [x] นำ **Celery** มาใช้เป็น Background Worker
*   [x] สร้าง Task สำหรับการดึงข้อมูลและสแกนสัญญาณเทรดสำหรับหุ้นทุกตัว
*   [x] บันทึกผลการคำนวณลง **Redis Cache**
*   [x] ปรับ API `/api/scan` ให้ดึงข้อมูลจาก Cache ทันที (ลด Response Time เหลือเสี้ยววินาที)

---

## 🚧 Phase 4: Security & Task Automation (Up Next)
**สถานะ:** **พร้อมดำเนินการ (รอการอนุมัติ)**
**เป้าหมาย:** ป้องกันการเข้าถึงข้อมูลโดยไม่ได้รับอนุญาต และสร้างระบบทำงานอัตโนมัติแบบ 100%
*   **JWT Authentication:** เพิ่มระบบสมัครสมาชิก (Register) และเข้าสู่ระบบ (Login) ด้วยอีเมลและรหัสผ่าน
*   **Authorization:** ล็อก API สำคัญ (`/api/portfolio`, `/api/paper-trade`) ให้เฉพาะผู้ใช้ที่ Login แล้วเท่านั้นที่เรียกใช้ได้ (ยกเลิกระบบ Hardcode User)
*   **Celery Beat (Cron Job):** ตั้งเวลาให้ระบบสแกนหุ้นทำงานเองทุกวัน จันทร์-ศุกร์ เวลา 17:30 น. (หลังตลาดหุ้นไทยปิด) โดยที่แอดมินไม่ต้องมากดรันคำสั่งเอง

---

## 🗓️ Phase 5: Frontend Integration & UI Polish (Future Plan)
**สถานะ:** รอวางแผน
**เป้าหมาย:** ปรับปรุงหน้าบ้าน (Static HTML/JS) ให้รองรับระบบใหม่
*   **Login Modal:** สร้างหน้าต่างสำหรับให้ผู้ใช้ล็อกอินเพื่อรับ Token
*   **Dynamic Watchlist:** ให้ผู้ใช้สามารถเลือกหุ้นเข้า Watchlist ส่วนตัวได้ (ปัจจุบันระบบบังคับสแกนหุ้น 10 ตัว)
*   **Error Handling:** ปรับปรุงการแจ้งเตือน (Toast Notification) ให้สวยงามและชัดเจนขึ้นเมื่อเซิร์ฟเวอร์ตอบกลับมา

## ☁️ Phase 6: Cloud Deployment & CI/CD (Future Plan)
**สถานะ:** รอวางแผน
**เป้าหมาย:** นำโปรเจกต์ขึ้นสู่ Public Cloud เพื่อให้ผู้ใช้งานจริงเข้าถึงได้
*   **Dockerization:** ทำ Dockerfile สำหรับ FastAPI Backend
*   **Cloud Hosting:** เลือกผู้ให้บริการ (เช่น AWS, GCP, หรือ DigitalOcean) เพื่อตั้งเซิร์ฟเวอร์
*   **CI/CD Pipeline:** เขียน GitHub Actions เพื่อสั่งให้ระบบ Deploy อัตโนมัติเมื่อมีการ Push โค้ดใหม่

---
*จัดทำโดย: Lead System Analyst*
