const mysql = require('mysql2/promise');

const pool = mysql.createPool({ host: process.env.DB_HOST, user: process.env.DB_USER, password: process.env.DB_PASSWORD || process.env.DB_PASS, database: process.env.DB_NAME, waitForConnections: true, connectionLimit: 10 });

(async () => {
  try {
    const conn = await pool.getConnection();
    await conn.ping();
    conn.release();
    console.log('MySQL connected OK');
  } catch (err) {
    console.error('MySQL connection failed:', err.message);
    console.log('Continuing without MySQL - using Flask/SQLite backend');
    // Non-fatal: Flask handles database operations via SQLite
  }
})();

module.exports = pool;


