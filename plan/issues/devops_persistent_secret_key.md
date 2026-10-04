# Issue: Fix JWT Token Invalidation on Server Restart (Persistent SECRET_KEY)

**Label:** `devops`, `bug`
**Status:** `To Do`
**Assignee:** DevOps / Backend Team

## Description
**ปัญหา:** เมื่อมีการรีสตาร์ทเซิร์ฟเวอร์หรือ Docker Containers ผู้ใช้งานที่เคยล็อกอินไว้จะถูกบังคับให้ออกจากระบบ (Log out) ทันที (เจอ 401 Unauthorized) ทำให้ผู้ใช้เข้าใจผิดว่าข้อมูลสูญหาย ทั้งๆ ที่ข้อมูลใน Database (TimescaleDB) ยังอยู่ครบ

**สาเหตุ:** คำสั่งแนะนำใน `README.md` บังคับให้สร้าง `SECRET_KEY` แบบสุ่มใหม่ทุกครั้งก่อนรัน Docker (`export SECRET_KEY="$(python3 -c 'import secrets; ...')"`) ทำให้ทุกครั้งที่เซิร์ฟเวอร์เปิดขึ้นมาใหม่ กุญแจที่ใช้เข้ารหัส JWT Token จะเปลี่ยนไป ทำให้ Token เก่าที่ผู้ใช้มีอยู่ใช้งานไม่ได้

## Acceptance Criteria
- [ ] สร้างและใช้งานไฟล์ `.env` สำหรับเก็บค่า `SECRET_KEY` ให้อยู่แบบถาวร (Persistent)
- [ ] แก้ไขเอกสาร `README.md` เพื่อเปลี่ยนคำแนะนำวิธีการ Start Server โดยให้ระบุขั้นตอนการสร้างและตั้งค่า `.env` แทนการใช้ `export` สร้างกุญแจใหม่ทุกครั้ง
- [ ] ยืนยันให้แน่ใจว่า `docker-compose.yml` สามารถดึงค่า `SECRET_KEY` จาก `.env` ได้อย่างถูกต้อง
- [ ] **การทดสอบ:** เมื่อผู้ใช้เข้าสู่ระบบแล้ว หากทำการ `docker compose down` และ `up` ใหม่ ผู้ใช้จะต้องไม่หลุดออกจากระบบ (Session must persist)
