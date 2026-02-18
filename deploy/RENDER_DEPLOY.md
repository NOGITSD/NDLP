# Deploy on Render.com (Free Tier)

## 1) แยก Dockerfile สำหรับ Render
Render ต้องการ Web Service แยกสำหรับ frontend และ backend แบบไม่ใช้ compose

### 1.1 Backend Web Service
สร้าง `Dockerfile` ที่ root สำหรับ backend (Render จะอ่านจาก root):
```dockerfile
# backend.Dockerfile (สำหรับ Render)
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY backend/ .
COPY project_jarvis/ /app/project_jarvis/
COPY skills/ /app/skills/

ENV PYTHONPATH="/app/project_jarvis:/app"
ENV APP_ENV=production

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", $PORT"]
```

### 1.2 Frontend Web Service
สร้าง `Dockerfile` สำหรับ frontend (static build):
```dockerfile
# frontend.Dockerfile (สำหรับ Render)
FROM node:20-alpine AS build

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY deploy/nginx-render.conf /etc/nginx/conf.d/default.conf

EXPOSE 8000
CMD ["nginx", "-g", "daemon off;"]
```

## 2) สร้าง nginx config สำหรับ Render
สร้าง `deploy/nginx-render.conf`:
```nginx
server {
    listen 8000;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass https://your-backend-service.onrender.com;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass https://your-backend-service.onrender.com;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 3) สร้าง Services บน Render

### 3.1 Backend Service
- Name: `jarvis-backend`
- Runtime: Docker
- Region: เลือกใกล้ตัว
- Branch: `main`
- Root Directory: (ว่าง คือ root)
- Dockerfile Path: `backend.Dockerfile`
- Instance Type: Free
- Environment Variables:
  - `PORT`: `8000`
  - `GROQ_API_KEY`: (ใส่ค่าจริง)
  - `DB_BACKEND`: `firebase`
  - `FIREBASE_CREDENTIALS`: (ใส่ชื่อไฟล์ JSON ที่อัปโหลด)
  - `GOOGLE_CLIENT_ID`: (ถ้าใช้ Google login)
- Auto-Deploy: เปิด

### 3.2 อัปโหลด Firebase Service Account
ในหน้า Service → Settings → Environment:
- Add File: `ndlp-ea287-firebase-adminsdk-fbsvc-0a7288a18e.json`
- อัปโหลดไฟล์ JSON จากเครื่อง

### 3.3 Frontend Service
- Name: `jarvis-frontend`
- Runtime: Docker
- Branch: `main`
- Root Directory: (ว่าง)
- Dockerfile Path: `frontend.Dockerfile`
- Instance Type: Free
- Build Args:
  - `VITE_GOOGLE_CLIENT_ID`: (ใส่ค่าจริง)
- Auto-Deploy: เปิด

### 3.4 แก้ URL ใน nginx-render.conf
หลัง deploy แล้วจะได้ URL:
- Backend: `https://jarvis-backend.onrender.com`
- Frontend: `https://jarvis-frontend.onrender.com`

แก้ `deploy/nginx-render.conf` ให้ชี้ไป backend URL จริง แล้ว push ใหม่

## 4) ทดสอบ
- เปิด `https://jarvis-frontend.onrender.com`
- ทดสอบ register/login/chat

## 5) ข้อจำกัด Free Tier
- หลัง 15 นาทีที่ไม่มี request จะ sleep (cold start)
- ตื่นขึ้นมาใช้ 5–10 วินาทีแรก
- ไม่สามารถรัน 24/7 ได้แบบ always-on

## 6) Update โค้ด
Push ไปที่ branch ที่เชื่อมกับ Render จะ auto-deploy ทันที

---

ถ้าต้องการ ผมสร้างไฟล์ Dockerfile + nginx config ให้พร้อม deploy บน Render ทันทีครับ.
