const express = require('express');
const cors = require('cors');
require('dotenv').config();
const multer = require('multer');
const upload = multer({ dest: 'uploads/' });
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');

const app = express();

// Try to load database, but don't fail if it's not available
// (We're using SQLite via Flask now, but Node.js routes might still be used for auth)
let db = null;
try {
  db = require('./config/db');
  console.log('✅ Node.js MySQL connection loaded (optional - Flask uses SQLite)');
} catch (err) {
  console.warn('⚠️  Node.js MySQL connection not available (this is OK - using Flask/SQLite)');
  console.warn('   Error:', err.message);
}

const corsOptions = {
  origin: ['http://localhost:5173','http://127.0.0.1:5173','http://localhost:3000','http://127.0.0.1:3000'],
  credentials: true,
  methods: ['GET','POST','PUT','DELETE','OPTIONS'],
  allowedHeaders: ['Content-Type','Authorization','Accept']
};
app.use(cors(corsOptions));
// app.options('*', cors(corsOptions)); // Removed - cors middleware handles OPTIONS

app.use(express.json());

// Serve uploaded images
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Routes (Note: These use MySQL, but Flask handles most operations via SQLite)
// These routes are optional - the app works with Flask alone
if (db) {
  app.use('/api/auth', require('./routes/auth'));
  app.use('/api/posts', require('./routes/posts'));
  app.use('/api/leaderboard', require('./routes/leaderboard'));
  app.use('/api/coupons', require('./routes/coupons'));
  app.use('/api/profile', require('./routes/profile'));
} else {
  // Provide placeholder routes if MySQL is not available
  app.use('/api/auth', (req, res, next) => {
    res.status(503).json({ error: 'Authentication service not available. Using Flask/SQLite backend.' });
  });
  app.use('/api/posts', (req, res, next) => {
    res.status(503).json({ error: 'Posts service not available. Using Flask/SQLite backend.' });
  });
  app.use('/api/leaderboard', (req, res, next) => {
    res.status(503).json({ error: 'Leaderboard service not available. Using Flask/SQLite backend.' });
  });
  app.use('/api/coupons', (req, res, next) => {
    res.status(503).json({ error: 'Coupons service not available. Using Flask/SQLite backend.' });
  });
  app.use('/api/profile', (req, res, next) => {
    res.status(503).json({ error: 'Profile service not available. Using Flask/SQLite backend.' });
  });
}

app.get('/api/auth/ping', (req, res) => {
  res.json({ status: 'ok', time: new Date().toISOString() });
});

app.get('/', (req, res) => {
  res.send('Backend running');
});

// Model prediction endpoint
app.post('/api/model/predict', upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }
  try {
    const form = new FormData();
    form.append('file', fs.createReadStream(req.file.path));

    const response = await axios.post('http://127.0.0.1:8000/predict', form, {
      headers: form.getHeaders(),
      timeout: 60000 // 60 seconds timeout for slow models
    });

    // Clean up uploaded file
    fs.unlink(req.file.path, (err) => {
      if (err) console.error('Failed to delete uploaded file:', err);
    });

    res.json(response.data);
  } catch (err) {
    console.error('Model prediction error:', err.message);
    res.status(500).json({ error: 'Model prediction failed', details: err.message });
  }
});

const PORT = process.env.PORT || 5000;

// new helper: poll an HTTP URL until it responds or timeout
async function waitForHttp(url, timeoutMs = 60000, intervalMs = 1500) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      await axios.get(url, { timeout: 2000 });
      return;
    } catch (err) {
      await new Promise(r => setTimeout(r, intervalMs));
    }
  }
  throw new Error(`Timeout waiting for ${url}`);
}

(async () => {
  // wait for model service (Streamlit or model API) to accept connections
  try {
    console.log('Waiting for model at http://127.0.0.1:8000...');
    await waitForHttp('http://127.0.0.1:8000', 60000);
    console.log('Model service is up (8000).');
  } catch (err) {
    console.warn('Model did not respond in time, continuing — model requests may fail until it starts.');
  }

  app.listen(PORT, '0.0.0.0')
    .on('listening', () => console.log(`Backend listening on ${PORT} (0.0.0.0)`))
    .on('error', (err) => { console.error('Server failed:', err && err.message); process.exit(1); });
})();


