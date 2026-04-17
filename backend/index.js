const express = require('express');
const cors = require('cors');
const app = express();

app.use(express.json());

// allow Vite dev server + allow credentials if you use cookies
app.use(cors({ origin: 'http://localhost:5173', credentials: true }));

// ...existing code...