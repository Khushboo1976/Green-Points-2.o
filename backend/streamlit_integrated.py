# streamlit_integrated.py
# Streamlit app integrated with frontend - opens when user clicks upload/take photo button

import streamlit as st
from PIL import Image
import io
import os
import sys
import json
import requests
from pathlib import Path

# Import model functions from greenpoints_app
try:
    import greenpoints_app
except ImportError:
    st.error("Error: Could not import greenpoints_app. Make sure it's in the same directory.")
    st.stop()

# -------------------------
# Config
# -------------------------
FLASK_API_URL = os.getenv("FLASK_API_URL", "http://127.0.0.1:7000")

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(
    page_title="Eco-Friendly Post Verification",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("🌱 Eco-Friendly Post Verification")
st.markdown("Upload your photo and description to verify your eco-friendly activity!")

# Get username from query params or session
try:
    username_param = st.query_params.get("username", None)
    if username_param:
        username = username_param
        st.session_state.username = username
    else:
        username = st.session_state.get("username", "user")
except Exception:
    username = st.session_state.get("username", "user")

st.info(f"👤 Logged in as: **{username}**")

# -------------------------
# Upload Section
# -------------------------
st.header("📤 Upload Your Eco-Friendly Activity")

# Option 1: File Upload
uploaded_file = st.file_uploader(
    "Choose an image file",
    type=["jpg", "jpeg", "png"],
    help="Upload a photo of your eco-friendly activity"
)

# Option 2: Camera
camera_image = st.camera_input("Or take a photo", help="Use your camera to capture the moment")

# Use whichever is available
image = None
if camera_image:
    image = Image.open(camera_image).convert("RGB")
    st.success("📷 Photo captured!")
elif uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.success("📁 File uploaded!")

# Description input
description = st.text_area(
    "Describe your eco-friendly activity",
    height=120,
    placeholder="E.g., Planted 5 trees in my neighborhood, Cleaned up the beach, Recycled 10 kg of plastic...",
    help="Provide a detailed description of what you did"
)

# Submit button
if st.button("✅ Verify & Submit", type="primary", use_container_width=True):
    if not image:
        st.error("⚠️ Please upload an image or take a photo first!")
    elif not description.strip():
        st.error("⚠️ Please provide a description of your activity!")
    else:
        with st.spinner("🔄 Analyzing your post with AI..."):
            try:
                # Save image temporarily
                img_bytes = io.BytesIO()
                image.save(img_bytes, format="JPEG")
                img_bytes.seek(0)
                
                # Prepare data for Flask API
                files = {"file": ("image.jpg", img_bytes, "image/jpeg")}
                data = {
                    "text": description,
                    "username": username
                }
                
                # Submit to Flask API (which calls FastAPI for AI analysis)
                api_url = f"{FLASK_API_URL}/analyze_post"
                response = requests.post(api_url, files=files, data=data, timeout=120)
                
                if response.status_code == 200:
                    result = response.json()
                    awarded_points = result.get("awardedPoints", 0)
                    updated_points = result.get("updatedPoints", 0)
                    category = result.get("category", "Other")
                    
                    st.success(f"✅ **Post Verified and Approved!**")
                    st.balloons()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Points Awarded", f"+{awarded_points}")
                    with col2:
                        st.metric("Total Points", updated_points)
                    with col3:
                        st.metric("Category", category)
                    
                    st.info("🎉 Your post has been added to the community feed!")
                    
                    # Store result in session state
                    st.session_state.last_result = {
                        "success": True,
                        "points": awarded_points,
                        "total_points": updated_points,
                        "category": category
                    }
                    
                    # If callback URL provided, notify frontend
                    if callback_url:
                        try:
                            # Send success notification to frontend
                            callback_response = requests.post(
                                callback_url,
                                json={
                                    "success": True,
                                    "points": awarded_points,
                                    "total_points": updated_points,
                                    "category": category,
                                    "message": "Post verified and added to feed"
                                },
                                timeout=5
                            )
                        except Exception as e:
                            st.warning(f"Could not notify frontend: {e}")
                    
                    # Notify parent window if in iframe
                    st.markdown("""
                    <script>
                        // Notify parent window immediately
                        if (window.parent !== window) {
                            window.parent.postMessage({
                                type: 'streamlit_post_success',
                                points: """ + str(awarded_points) + """,
                                total_points: """ + str(updated_points) + """,
                                category: '""" + category + """'
                            }, '*');
                        }
                    </script>
                    """, unsafe_allow_html=True)
                    
                    # Add a close button that also sends message
                    if st.button("✅ Close", use_container_width=True):
                        st.markdown("""
                        <script>
                            if (window.parent !== window) {
                                window.parent.postMessage({type: 'streamlit_close'}, '*');
                            }
                        </script>
                        """, unsafe_allow_html=True)
                        st.stop()
                    
                else:
                    error_msg = response.json().get("error", "Unknown error")
                    st.error(f"❌ **Post Rejected:** {error_msg}")
                    st.session_state.last_result = {"success": False, "error": error_msg}
                    
            except Exception as e:
                st.error(f"❌ **Error:** {str(e)}")
                st.exception(e)
                st.session_state.last_result = {"success": False, "error": str(e)}

# -------------------------
# Instructions
# -------------------------
with st.expander("ℹ️ How it works"):
    st.markdown("""
    1. **Upload or take a photo** of your eco-friendly activity
    2. **Describe** what you did in detail
    3. **Click Verify & Submit** - our AI will analyze your post
    4. **Get points** if your post is verified
    5. **Your post** will appear in the community feed
    
    **Categories:**
    - 🌳 Tree Plantation (50 points)
    - 🧹 Cleanliness Drive (40 points)
    - ♻️ Recycling/Waste Management (45 points)
    - 📢 Awareness Campaign (30 points)
    - 🪴 Composting (35 points)
    - 🌍 Other (20 points)
    """)

# -------------------------
# Close button (for iframe) - only show if not already closed
# -------------------------
if 'last_result' not in st.session_state or not st.session_state.get('last_result', {}).get('success', False):
    if st.button("❌ Close", use_container_width=True):
        st.markdown("""
        <script>
            if (window.parent !== window) {
                window.parent.postMessage({type: 'streamlit_close'}, '*');
            } else {
                window.close();
            }
        </script>
        """, unsafe_allow_html=True)
        st.stop()

