# MySQL Database Queries Documentation

This document contains all MySQL queries used in the Eco-Friendly Community project.

## Database Connection

- **Host**: localhost (configurable via `DB_HOST` in `config.env`)
- **Database**: green_points
- **User**: root (configurable via `DB_USER` in `config.env`)
- **Password**: (configurable via `DB_PASSWORD` in `config.env`)

## Database Schema

### Tables
1. `users` - User accounts
2. `profiles` - User profile information
3. `email_verifications` - Email verification tokens
4. `phone_otps` - Phone OTP verification
5. `posts` - User posts
6. `post_images` - Images associated with posts
7. `image_hash_index` - Image hash index for duplicate detection
8. `points_transactions` - Points transaction history
9. `leaderboard` - User points leaderboard
10. `coupons` - Available coupons
11. `coupon_redemptions` - Coupon redemption records

## Queries by File

### 1. flask_app.py - `/analyze_post` endpoint

#### Get User by Username
```sql
SELECT id FROM users WHERE username = %s
```
**Purpose**: Check if user exists before creating post
**Returns**: User ID if exists, None otherwise

#### Create User (if doesn't exist)
```sql
INSERT INTO users (username, email, password_hash, is_email_verified) 
VALUES (%s, %s, %s, %s)
```
**Purpose**: Create a new user if username doesn't exist
**Parameters**: 
- username
- email (generated as `{username}@example.com`)
- password_hash (temporary: `temp_hash`)
- is_email_verified (True)

#### Update Leaderboard Points
```sql
INSERT INTO leaderboard (user_id, points) 
VALUES (%s, %s) 
ON DUPLICATE KEY UPDATE points = points + %s
```
**Purpose**: Add points to user's total, creating entry if doesn't exist
**Parameters**: user_id, points_awarded, points_awarded
**Returns**: Updates or creates leaderboard entry

#### Insert Post (Full Schema)
```sql
INSERT INTO posts (user_id, post_text, status, created_at)
VALUES (%s, %s, %s, %s)
```
**Purpose**: Create a new post with full schema
**Parameters**: user_id, post_text, status ('approved'), created_at
**Fallback**: If this fails, tries simplified version below

#### Insert Post (Simplified Schema)
```sql
INSERT INTO posts (user_id, post_text) 
VALUES (%s, %s)
```
**Purpose**: Fallback if full schema insert fails
**Parameters**: user_id, post_text

#### Get Updated Points
```sql
SELECT points FROM leaderboard WHERE user_id = %s
```
**Purpose**: Get user's total points after update
**Returns**: Current points total

### 2. routes/posts.js - GET `/community` endpoint

#### Get Community Posts
```sql
SELECT 
    p.id                 AS post_id,
    p.user_id            AS user_id,
    u.username           AS username,
    u.email              AS email,
    pr.profile_image_url AS profile_image_url,
    p.title              AS title,
    p.description        AS description,
    p.post_text          AS post_text,
    p.external_url       AS external_url,
    p.created_at         AS created_at,
    p.updated_at         AS updated_at,
    pi.id                AS image_id,
    pi.image_url         AS image_url,
    pi.phash             AS phash,
    pi.width             AS width,
    pi.height            AS height
FROM posts p
INNER JOIN users u ON u.id = p.user_id
LEFT JOIN profiles pr ON pr.user_id = p.user_id
LEFT JOIN post_images pi ON pi.post_id = p.id
WHERE p.status = 'approved'
ORDER BY p.created_at DESC, pi.id ASC
```
**Purpose**: Fetch all approved posts with user info and images
**Returns**: Array of posts with aggregated images
**Notes**: 
- Only returns posts with status='approved'
- Orders by creation date (newest first)
- Aggregates multiple images per post in application code

### 3. Database Schema (schema.sql)

#### Create Database
```sql
CREATE DATABASE IF NOT EXISTS green_points;
USE green_points;
```

#### Create Users Table
```sql
CREATE TABLE IF NOT EXISTS users (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  is_email_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Create Profiles Table
```sql
CREATE TABLE IF NOT EXISTS profiles (
  user_id BIGINT PRIMARY KEY,
  phone VARCHAR(20) UNIQUE,
  is_phone_verified BOOLEAN DEFAULT FALSE,
  location VARCHAR(255),
  gender ENUM('male','female','other','prefer_not') NULL,
  age INT NULL,
  occasion VARCHAR(255) NULL,
  profile_image_url VARCHAR(1024) NULL,
  profile_completed BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Create Posts Table
```sql
CREATE TABLE IF NOT EXISTS posts (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  title VARCHAR(255),
  description TEXT,
  post_text TEXT,
  status ENUM('pending','approved','rejected') DEFAULT 'pending',
  external_url VARCHAR(1024) NULL,
  streamlit_verdict JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX (status),
  FULLTEXT (title, description, post_text)
);
```

#### Create Post Images Table
```sql
CREATE TABLE IF NOT EXISTS post_images (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  post_id BIGINT NOT NULL,
  image_url VARCHAR(1024) NOT NULL,
  phash VARCHAR(64) NULL,
  width INT NULL,
  height INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
  INDEX (phash)
);
```

#### Create Leaderboard Table
```sql
CREATE TABLE IF NOT EXISTS leaderboard (
  user_id BIGINT PRIMARY KEY,
  points INT DEFAULT 0,
  last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Create Points Transactions Table
```sql
CREATE TABLE IF NOT EXISTS points_transactions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  post_id BIGINT NULL,
  points INT NOT NULL,
  reason VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE SET NULL
);
```

## Transaction Flow

### Post Submission Flow (flask_app.py)

1. **Validate Input**: Check file, text, and username
2. **Save File**: Save uploaded image to `uploads/` directory
3. **Forward to AI Service**: Send to FastAPI `/analyze` endpoint
4. **Check AI Result**: If `allow=False`, reject and cleanup
5. **Database Transaction**:
   - Get or create user
   - Update leaderboard points
   - Insert post record
   - Get updated points total
6. **Return Response**: Return success with points awarded

### Error Handling

- **Database Errors**: Rollback transaction, cleanup uploaded file
- **AI Service Unavailable**: Return 503 error, cleanup file
- **Invalid Content**: Reject post, cleanup file, return error

## Connection Pooling

### pymysql (flask_app.py)
```python
conn = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False,
)
```

### mysql-connector-python (db.py)
```python
POOL = pooling.MySQLConnectionPool(
    pool_name="gp_pool",
    pool_size=5,
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    autocommit=False
)
```

## Indexes

- `users.username` - UNIQUE index
- `users.email` - UNIQUE index
- `posts.status` - INDEX for filtering approved posts
- `posts.title, description, post_text` - FULLTEXT index for search
- `post_images.phash` - INDEX for duplicate detection
- `profiles.phone` - UNIQUE index
- `leaderboard.user_id` - PRIMARY KEY

## Notes

- All foreign keys use `ON DELETE CASCADE` or `ON DELETE SET NULL`
- Timestamps use `CURRENT_TIMESTAMP` for created_at
- Updated_at uses `ON UPDATE CURRENT_TIMESTAMP`
- Leaderboard uses `ON DUPLICATE KEY UPDATE` for upsert operations
- Posts default to 'pending' status
- Points are stored in both `leaderboard` table (aggregated) and `points_transactions` table (history)