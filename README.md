# Smart City Environmental Monitoring & Alert System (SCEMAS)
## Course: 3A04 Project Software Design II (SE3A04)

A comprehensive environmental monitoring and alerting system designed for smart cities. SCEMAS provides real-time monitoring of environmental sensors, data processing, and intelligent alert mechanisms across multiple platforms.

---

## 📋 Table of Contents
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Deliverables](#deliverables)

---

## 📁 Project Structure

```
SCEMAS/
├── frontend/                 # Web application (React + Electron)
├── Mobileapp/               # Mobile app (React Native with Expo)
├── Backend/                 # Microservices (Python)
│   ├── services/            # 5 agent microservices
│   │   ├── accounts/        # User account management
│   │   ├── alerts/          # Alert generation & notifications
│   │   ├── city/            # City-level data management
│   │   ├── data_processing/ # Analytics & data processing
│   │   └── public/          # Public data APIs
│   └── shared/              # Common utilities & schemas
├── ExternalSensorData/      # Sensor data simulation
└── Deliverables/            # Documentation (LaTeX)
```

---

## 🛠️ Tech Stack

### **Frontend (Web Application)**
| Layer | Technologies |
|-------|--------------|
| **Framework** | React 18.2, TypeScript 5.2 |
| **Build Tool** | Vite 5.0 |
| **Desktop** | Electron 28 |
| **Routing** | React Router v6.21 |
| **Styling** | Tailwind CSS 3.4, PostCSS |
| **Mapping** | Leaflet 1.9.4, react-leaflet 4.2.1 |
| **Icons** | Lucide React 1.7 |
| **Auth/Database** | Supabase 2.39.0 |

### **Mobile Application**
| Layer | Technologies |
|-------|--------------|
| **Framework** | React Native 0.81.5 via Expo 54.0 |
| **Language** | TypeScript 5.9 |
| **Routing** | Expo Router 6.0 |
| **Navigation** | React Navigation 7.1 (bottom tabs) |
| **Mapping** | React Native Maps 1.20.1 |
| **Animations** | React Native Reanimated 4.1 |
| **Gestures** | React Native Gesture Handler 2.28 |
| **Auth/Database** | Supabase 2.101 |
| **Platforms** | iOS, Android, Web |

### **Backend (Microservices)**
| Layer | Technologies |
|-------|--------------|
| **Framework** | FastAPI |
| **Language** | Python |
| **Orchestration** | Docker & Docker Compose |
| **Database** | Supabase (PostgreSQL) |
| **Architecture Pattern** | Microservices with Agent-based design |

---

## 🏗️ Architecture

### System Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                              │
├──────────────────────┬──────────────────────┬────────────────┤
│   Web App            │   Mobile App         │   Desktop App  │
│  (React/Vite)        │ (React Native/Expo)  │   (Electron)   │
└──────────────────────┴──────────────────────┴────────────────┘
                          ↓ REST/WebSocket
┌─────────────────────────────────────────────────────────────┐
│          Authentication & Database Layer                     │
│               Supabase (PostgreSQL)                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                Backend Services Layer                        │
├──────────────────────────────────────────────────────────────┤
│ Accounts   │ Alerts   │ City     │ Data Proc.  │ Public API  │
│ (Port 8005)│(Port 8004)│(Port 8001)│(Port 8003)│(Port 8002)  │
│ FastAPI    │ FastAPI  │ FastAPI  │ FastAPI    │ FastAPI     │
└──────────────────────────────────────────────────────────────┘
                          ↑
┌─────────────────────────────────────────────────────────────┐
│            External Data Sources                            │
├──────────────────────────────────────────────────────────────┤
│  Sensor Arrays  │  IoT Devices  │  Weather Data              │
└──────────────────────────────────────────────────────────────┘
```

### Microservices Description

| Service | Port | Purpose |
|---------|------|---------|
| **Accounts** | 8005 | User authentication, profile management, role-based access control |
| **Alerts** | 8004 | Alert rules, notification management, threshold monitoring |
| **City** | 8001 | City-level data aggregation, sensor management, zone coordination |
| **Data Processing** | 8003 | Data analysis, real-time processing, trend analysis, predictions |
| **Public** | 8002 | Public API endpoints, data exposure, reporting interfaces |

### Shared Components
- Common schemas and data models
- Exception handling utilities
- Observer pattern for event-driven communication
- Shared validation & business logic

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ (for frontend/mobile development)
- Python 3.10+ (for backend services)
- Docker & Docker Compose
- Supabase account and credentials

### Frontend Setup
```bash
cd frontend
npm install
npm run dev           # Start development server on :5173
npm run build         # Build for production
npm run build:electron # Build Electron desktop app
```

### Mobile App Setup
```bash
cd Mobileapp/SCEMAS_Public_App
npm install
npm start             # Start Expo CLI
npm run android       # Run on Android
npm run ios           # Run on iOS
npm run web           # Run on web
```

### Backend Setup
```bash
cd Backend
docker-compose up -d  # Start all microservices
# Services will be available at localhost:8001-8005
```

### External Sensor Data
```bash
cd ExternalSensorData
python send_data.py   # Simulate and send sensor data
```

---

## 📚 Deliverables

The [Deliverables](Deliverables/) folder contains:
- **D1**: Initial system requirements and design specifications
- **D2**: Software architecture and detailed design documentation
- **D3**: Implementation, testing, and deployment documentation

All documentation is provided in LaTeX format.

---

## 🔑 Key Features

✅ Real-time environmental sensor monitoring  
✅ Multi-platform support (Web, Desktop, Mobile)  
✅ Intelligent alert system with customizable thresholds  
✅ User authentication and role-based access control  
✅ Data analytics and trend analysis  
✅ City-wide data aggregation and visualization  
✅ Responsive mapping interface with Leaflet/React Native Maps  
✅ Scalable microservices architecture  

---

## 📝 Notes

- Frontend folder referenced as `[Webapp](Webapp/)` in original structure; actual location is `frontend/`
- Mobile app is the creative feature implementation
- All backend services share a common Python package located in `Backend/shared/`
- Services auto-restart unless stopped explicitly 
