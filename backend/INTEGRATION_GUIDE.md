# Frontend-Streamlit Integration Guide

## Overview

This guide explains how the frontend and Streamlit work together to verify and submit eco-friendly posts.

## Architecture

```
Frontend (React) → Streamlit (Modal/Iframe) → Flask API → FastAPI (AI) → SQLite DB
                     ↓
                Post Verified
                     ↓
            Frontend Refreshes Feed
```

## Components

### 1. Frontend (React)
- **UploadSection.tsx**: Main upload component with buttons
- Opens Streamlit in a modal/iframe when "Take Photo" or "Upload File" is clicked
- Listens for postMessage from Streamlit to refresh feed

### 2. Streamlit (Python)
- **streamlit_integrated.py**: Streamlit app for verification
- Receives username from URL parameters
- Allows user to upload/take photo and enter description
- Calls Flask API to verify and submit post
- Sends postMessage to parent window on success

### 3. Flask API (Python)
- **flask_app.py**: Main API server
- Uses SQLite database (no MySQL needed)
- Handles post submission and point updates
- Serves community feed data

### 4. FastAPI (Python)
- **model_api.py**: AI model service
- Analyzes images and text
- Returns verification result and points

## Setup Instructions

### 1. Setup SQLite Database

```bash
cd backend
python setup_sqlite.py
```

This creates `green_points.db` with all necessary tables.

### 2. Update Streamlit to Use Integrated Version

Update `start_all_windows.bat` to use the integrated Streamlit:

```bat
start "Streamlit ML UI (8501)" cmd /k "cd /d %BACKEND_DIR% && %PYTHON_EXE% -m streamlit run streamlit_integrated.py --server.port 8501"
```

Or run manually:
```bash
cd backend
streamlit run streamlit_integrated.py --server.port 8501
```

### 3. Start All Services

```bash
start_all_windows.bat
```

Or start individually:
1. FastAPI (port 8000): `uvicorn model_api:app --host 127.0.0.1 --port 8000`
2. Flask (port 7000): `python flask_app.py`
3. Streamlit (port 8501): `streamlit run streamlit_integrated.py --server.port 8501`
4. Frontend (port 3000): `npm run dev`

## How It Works

### User Flow

1. **User clicks "Take Photo" or "Upload File"** in frontend
2. **Frontend opens Streamlit in modal** with username parameter
3. **User uploads photo and enters description** in Streamlit
4. **Streamlit calls Flask API** (`/analyze_post`) with image and text
5. **Flask API calls FastAPI** to analyze the post
6. **FastAPI returns verification result** (points, category, approved/rejected)
7. **Flask API saves to SQLite** and updates user points
8. **Streamlit sends postMessage** to frontend with success data
9. **Frontend refreshes feed** and updates points
10. **Modal closes** and user sees updated feed

### API Endpoints

#### Flask API

- `POST /analyze_post`: Submit post for verification
  - Parameters: `file`, `text`, `username`
  - Returns: `{awardedPoints, updatedPoints, category, message}`
  
- `GET /api/community`: Get all approved posts
  - Returns: `{posts: [...]}`
  
- `GET /api/user/<username>/points`: Get user points
  - Returns: `{points: number}`

#### FastAPI

- `POST /analyze`: Analyze image and text
  - Parameters: `file`, `text`, `username`
  - Returns: `{allow, points, category}`

### Communication Between Frontend and Streamlit

#### Frontend → Streamlit
- Opens Streamlit in iframe with URL: `http://localhost:8501/?username=USERNAME`

#### Streamlit → Frontend
- Sends postMessage on success:
  ```javascript
  window.parent.postMessage({
    type: 'streamlit_post_success',
    points: 50,
    total_points: 2500,
    category: 'Tree Plantation'
  }, '*');
  ```

#### Frontend Listens
```javascript
window.addEventListener('message', (event) => {
  if (event.origin !== 'http://localhost:8501') return;
  if (event.data.type === 'streamlit_post_success') {
    // Update points, refresh feed, close modal
  }
});
```

## Database Schema (SQLite)

Key tables:
- `users`: User accounts
- `posts`: User posts
- `post_images`: Post images
- `leaderboard`: User points
- `points_transactions`: Points history

## Troubleshooting

### Streamlit not opening in modal
- Check CORS settings in Flask
- Verify Streamlit is running on port 8501
- Check browser console for errors

### Posts not appearing in feed
- Check Flask API `/api/community` endpoint
- Verify posts are being saved to SQLite
- Check post status is 'approved'

### Points not updating
- Check Flask API `/api/user/<username>/points` endpoint
- Verify leaderboard table is being updated
- Check browser network tab for API calls

### Streamlit not sending messages
- Check Streamlit console for errors
- Verify postMessage is being sent
- Check browser console for received messages

## Files Modified

1. **backend/flask_app.py**: Converted to SQLite, added CORS, added community endpoint
2. **backend/streamlit_integrated.py**: New integrated Streamlit app
3. **backend/schema_sqlite.sql**: SQLite schema
4. **backend/setup_sqlite.py**: Database setup script
5. **src/components/UploadSection.tsx**: Added Streamlit modal integration
6. **src/App.tsx**: Added callbacks for post submission and points update
7. **src/components/CommunityFeed.tsx**: Fetches from Flask API

## Next Steps

1. Test the integration by clicking "Take Photo" or "Upload File"
2. Verify posts appear in community feed
3. Check points are updated in profile
4. Test with multiple users

## Notes

- SQLite is file-based, no server needed
- All data is stored in `backend/green_points.db`
- Streamlit runs in iframe for seamless integration
- Frontend automatically refreshes after post submission
- Points are updated in real-time

