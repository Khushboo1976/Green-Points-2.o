-- SQLite Schema for Eco-Friendly Community
-- Run this to create the database: sqlite3 green_points.db < schema_sqlite.sql

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  is_email_verified INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
  user_id INTEGER PRIMARY KEY,
  phone TEXT UNIQUE,
  is_phone_verified INTEGER DEFAULT 0,
  location TEXT,
  gender TEXT CHECK(gender IN ('male','female','other','prefer_not')),
  age INTEGER,
  occasion TEXT,
  profile_image_url TEXT,
  profile_completed INTEGER DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_verifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  token TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  used INTEGER DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_email_verifications_token ON email_verifications(token);

CREATE TABLE IF NOT EXISTS phone_otps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  phone TEXT,
  otp_hash TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP,
  used INTEGER DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_phone_otps_phone ON phone_otps(phone);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  title TEXT,
  description TEXT,
  post_text TEXT,
  status TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
  external_url TEXT,
  streamlit_verdict TEXT, -- JSON stored as TEXT
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);

CREATE TABLE IF NOT EXISTS post_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id INTEGER NOT NULL,
  image_url TEXT NOT NULL,
  phash TEXT,
  width INTEGER,
  height INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_post_images_post_id ON post_images(post_id);
CREATE INDEX IF NOT EXISTS idx_post_images_phash ON post_images(phash);

CREATE TABLE IF NOT EXISTS image_hash_index (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phash TEXT NOT NULL,
  post_image_id INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (post_image_id) REFERENCES post_images(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_image_hash_index_phash ON image_hash_index(phash);

CREATE TABLE IF NOT EXISTS points_transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  post_id INTEGER,
  points INTEGER NOT NULL,
  reason TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_points_transactions_user_id ON points_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_points_transactions_post_id ON points_transactions(post_id);

CREATE TABLE IF NOT EXISTS leaderboard (
  user_id INTEGER PRIMARY KEY,
  points INTEGER DEFAULT 0,
  last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS coupons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  description TEXT,
  amount_value REAL,
  quantity INTEGER DEFAULT 1,
  redeemed_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coupon_redemptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  coupon_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (coupon_id) REFERENCES coupons(id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  UNIQUE(coupon_id, user_id)
);

-- Trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_posts_timestamp 
AFTER UPDATE ON posts
BEGIN
  UPDATE posts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_profiles_timestamp 
AFTER UPDATE ON profiles
BEGIN
  UPDATE profiles SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
END;

CREATE TRIGGER IF NOT EXISTS update_leaderboard_timestamp 
AFTER UPDATE ON leaderboard
BEGIN
  UPDATE leaderboard SET last_update = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
END;

