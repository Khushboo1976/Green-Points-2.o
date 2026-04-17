# SQLite Integration - Complete Setup Guide

## ✅ What's Been Done

### 1. Database Migration: MySQL → SQLite
- ✅ Removed MySQL dependencies (pymysql)
- ✅ Created SQLite schema (`schema_sqlite.sql`)
- ✅ Created database setup script (`setup_sqlite.py`)
- ✅ Updated Flask app to use SQLite
- ✅ Database auto-creates on first run

### 2. Frontend-Streamlit Integration
- ✅ Created integrated Streamlit app (`streamlit_integrated.py`)
- ✅ Updated UploadSection to open Streamlit in modal
- ✅ Added postMessage communication between frontend and Streamlit
- ✅ Auto-refresh feed after post submission
- ✅ Auto-update points after post submission

### 3. API Endpoints
- ✅ `POST /analyze_post` - Submit post for verification
- ✅ `GET /api/community` - Get all approved posts
- ✅ `GET /api/user/<username>/points` - Get user points
- ✅ `GET /uploads/<filename>` - Serve uploaded images

## 🚀 Quick Start

### Step 1: Setup Database
```bash
cd backend
python setup_sqlite.py
```

### Step 2: Start Services
```bash
# Option 1: Use batch script (Windows)
start_all_windows.bat

# Option 2: Start manually
# Terminal 1: FastAPI
cd backend
python -m uvicorn model_api:app --host 127.0.0.1 --port 8000

# Terminal 2: Flask API
cd backend
python flask_app.py

# Terminal 3: Streamlit
cd backend
streamlit run streamlit_integrated.py --server.port 8501

# Terminal 4: Frontend
npm run dev
```

## 📁 Database Location
- **File**: `backend/green_points.db`
- **Type**: SQLite (file-based, no server needed)
- **Backup**: Just copy the .db file

## 🔄 User Flow

1. User clicks **"Take Photo"** or **"Upload File"** in frontend
2. Streamlit opens in **modal/iframe** with username
3. User uploads photo and enters description
4. Streamlit calls Flask API (`/analyze_post`)
5. Flask API calls FastAPI for AI analysis
6. Flask API saves to SQLite and updates points
7. Streamlit sends postMessage to frontend
8. Frontend refreshes feed and updates points
9. Modal closes automatically

## 🧪 Testing

### Test Database
```bash
cd backend
python -c "import sqlite3; conn = sqlite3.connect('green_points.db'); print('✅ Connected'); conn.close()"
```

### Test API
```bash
# Test community endpoint
curl http://127.0.0.1:7000/api/community

# Test user points
curl http://127.0.0.1:7000/api/user/test_user/points
```

### Test Frontend Integration
1. Open http://localhost:3000
2. Click "Take Photo" or "Upload File"
3. Streamlit should open in modal
4. Upload photo and submit
5. Verify feed updates and points increase

## 📊 Database Schema

Key tables:
- `users` - User accounts
- `posts` - User posts
- `post_images` - Post images
- `leaderboard` - User points
- `points_transactions` - Points history

## 🔧 Configuration

### Environment Variables
```env
FLASK_API_URL=http://127.0.0.1:7000
FASTAPI_ANALYZE_URL=http://127.0.0.1:8000/analyze
DB_PATH=green_points.db
FLASK_PORT=7000
```

### Streamlit Config
- Port: 8501
- Headless: true
- CORS: enabled

## 🐛 Troubleshooting

### Database Issues
- **Not found**: Run `python setup_sqlite.py`
- **Locked**: Close other connections
- **Permissions**: Check file permissions

### Streamlit Not Opening
- Check port 8501 is available
- Check CORS settings
- Check browser console for errors

### Posts Not Appearing
- Check `/api/community` endpoint
- Verify posts in database
- Check post status is 'approved'

### Points Not Updating
- Check `/api/user/<username>/points` endpoint
- Verify leaderboard table
- Check browser network tab

## 📝 Files Modified

### Backend
- `flask_app.py` - SQLite integration, CORS, endpoints
- `streamlit_integrated.py` - New integrated Streamlit app
- `schema_sqlite.sql` - SQLite schema
- `setup_sqlite.py` - Database setup
- `requirements.txt` - Removed pymysql, added flask-cors

### Frontend
- `UploadSection.tsx` - Streamlit modal integration
- `App.tsx` - Callbacks for post submission
- `CommunityFeed.tsx` - Fetches from Flask API

## ✨ Benefits

✅ **No MySQL server** - File-based database
✅ **Easy setup** - No installation required
✅ **Portable** - Easy to backup
✅ **Fast** - Good performance
✅ **No connectivity issues** - No network required
✅ **Seamless integration** - Streamlit in modal
✅ **Auto-refresh** - Feed updates automatically
✅ **Real-time points** - Points update immediately

## 🎯 Next Steps

1. **Test the integration** - Click buttons and verify
2. **Check database** - View posts in SQLite
3. **Verify points** - Check points update correctly
4. **Test multiple users** - Create posts from different users

## 📚 Additional Resources

- `INTEGRATION_GUIDE.md` - Detailed integration guide
- `SETUP_SQLITE_INTEGRATION.md` - Setup instructions
- `MYSQL_QUERIES.md` - Database queries (now SQLite)

## 🎉 Summary

**All integration complete!**

- ✅ SQLite database
- ✅ Frontend-Streamlit integration
- ✅ Post submission workflow
- ✅ Points update system
- ✅ Community feed integration
- ✅ Auto-refresh functionality

**Ready to test!** Start all services and try it out! 🚀

