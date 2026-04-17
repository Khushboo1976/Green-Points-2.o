# greenpoints_app.py
import streamlit as st
from PIL import Image
import io, hashlib, time
import os
import torch
from transformers import (
    AutoProcessor, CLIPModel,
    BlipProcessor, BlipForConditionalGeneration,
    pipeline
)
import sys
import json
import requests

# -------------------------
# Config (tuneable)
# -------------------------
CLIP_SIM_THRESHOLD = 0.28          # similarity threshold (tuneable)
ZERO_SHOT_THRESHOLD = 0.40         # zero-shot category confidence threshold
TOXICITY_THRESHOLD = 0.50          # if any toxic label > this -> flagged
NSFW_THRESHOLD = 0.50              # if NSFW image score > this -> flagged
MISUSE_PENALTY = 50                # points to deduct on misuse/NSFW
DUPLICATE_REJECT = True

CATEGORY_LABELS = [
    "Tree Plantation",
    "Cleanliness Drive",
    "Recycling/Waste Management",
    "Awareness Campaign",
    "Composting",
    "Other"
]

CATEGORY_POINTS = {
    "Tree Plantation": 50,
    "Cleanliness Drive": 40,
    "Recycling/Waste Management": 45,
    "Awareness Campaign": 30,
    "Composting": 35,
    "Other": 20
}

# -------------------------
# Utilities
# -------------------------
def img_hash_bytes(image: Image.Image):
    b = io.BytesIO()
    image.save(b, format="PNG")
    return hashlib.md5(b.getvalue()).hexdigest()

def text_hash(s: str):
    return hashlib.md5(s.strip().lower().encode()).hexdigest()

# -------------------------
# Model loading (cached)
# -------------------------
def _load_models_impl():
    """Internal implementation of model loading with progress feedback."""
    device = 0 if torch.cuda.is_available() else -1
    print(f"🖥️  Using device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")

    try:
        # CLIP (contrastive, image-text similarity)
        print("  → Loading CLIP model and processor...")
        sys.stdout.flush()
        clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        clip_processor = AutoProcessor.from_pretrained("openai/clip-vit-base-patch32")
        if torch.cuda.is_available():
            clip_model.to("cuda")
        print("  ✅ CLIP loaded")

        # BLIP captioning (Salesforce/blip-image-captioning-base)
        print("  → Loading BLIP model and processor...")
        sys.stdout.flush()
        blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        if torch.cuda.is_available():
            blip_model.to("cuda")
        print("  ✅ BLIP loaded")

        # Zero-shot classifier (text) - facebook/bart-large-mnli
        print("  → Loading Zero-shot classifier...")
        sys.stdout.flush()
        zero_shot = pipeline("zero-shot-classification",
                             model="facebook/bart-large-mnli",
                             device=device)
        print("  ✅ Zero-shot classifier loaded")

        # Toxicity / moderation (text)
        print("  → Loading Toxicity detector...")
        sys.stdout.flush()
        toxic_pipe = pipeline("text-classification",
                              model="unitary/toxic-bert",
                              device=device, return_all_scores=True)
        print("  ✅ Toxicity detector loaded")

        # NSFW image classifier (Falconsai or similar)
        print("  → Loading NSFW detector...")
        sys.stdout.flush()
        nsfw_pipe = None
        try:
            nsfw_pipe = pipeline("image-classification", model="Falconsai/nsfw_image_detection", device=device)
            print("  ✅ NSFW detector loaded")
        except Exception as e:
            # fallback None if not available
            print(f"  ⚠️  NSFW model not available (optional): {e}")
            nsfw_pipe = None

        return {
            "clip_model": clip_model,
            "clip_processor": clip_processor,
            "blip_model": blip_model,
            "blip_processor": blip_processor,
            "zero_shot": zero_shot,
            "toxic_pipe": toxic_pipe,
            "nsfw_pipe": nsfw_pipe,
            "device": device
        }
    except Exception as e:
        error_msg = f"Failed to load AI models: {e}. Make sure you have internet connection for first-time model downloads."
        print(f"  ❌ ERROR: {error_msg}")
        raise RuntimeError(error_msg)

# Try to use Streamlit cache if available
try:
    @st.cache_resource
    def load_models():
        """Load AI models with Streamlit caching."""
        return _load_models_impl()
except (NameError, AttributeError):
    # Not in Streamlit context - define without cache
    def load_models():
        """Load AI models without caching."""
        return _load_models_impl()

# Lazy model loading - only load when needed (Streamlit context)
_models = None

def get_models():
    """Get models, loading them if not already loaded."""
    global _models
    if _models is None:
        _models = load_models()
    return _models

# -------------------------
# Inference helpers
# -------------------------
def generate_caption(image: Image.Image):
    models = get_models()
    proc = models["blip_processor"]
    model = models["blip_model"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    inputs = proc(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=32)
    caption = proc.decode(out[0], skip_special_tokens=True)
    return caption

def clip_similarity(image: Image.Image, text: str):
    models = get_models()
    proc = models["clip_processor"]
    model = models["clip_model"]
    device = "cuda" if torch.cuda.is_available() else "cpu"

    image_inputs = proc(images=image, return_tensors="pt").to(device)
    text_inputs = proc(text=[text], return_tensors="pt", padding=True).to(device)

    with torch.no_grad():
        image_emb = model.get_image_features(**image_inputs)
        text_emb = model.get_text_features(**text_inputs)

    image_emb = image_emb / image_emb.norm(p=2, dim=-1, keepdim=True)
    text_emb = text_emb / text_emb.norm(p=2, dim=-1, keepdim=True)

    sim = (image_emb @ text_emb.T).item()
    return sim

def run_zero_shot(text: str):
    models = get_models()
    classifier = models["zero_shot"]
    res = classifier(text, candidate_labels=CATEGORY_LABELS, hypothesis_template="This example is about {}.")
    # res contains 'labels' and 'scores'
    return res

def moderate_text(text: str, threshold=TOXICITY_THRESHOLD):
    models = get_models()
    toxic = models["toxic_pipe"]
    res = toxic(text)
    # normalize output format
    # If return_all_scores=True, res might be [[{label, score}, ...]] or list
    items = res[0] if isinstance(res[0], list) else res
    flagged = False
    flags = []
    for it in items:
        lbl = it.get("label", "").lower()
        score = float(it.get("score", 0.0))
        if score >= threshold:
            flagged = True
            flags.append({"label": lbl, "score": score})
    return flagged, items

def check_nsfw(image: Image.Image, threshold=NSFW_THRESHOLD):
    models = get_models()
    nsfw_pipe = models.get("nsfw_pipe", None)
    if nsfw_pipe is None:
        return False, None
    res = nsfw_pipe(image)
    # res might be [{'label': 'normal', 'score': 0.9}, ...]
    # find nsfw label
    for r in res:
        lbl = r.get("label", "").lower()
        score = float(r.get("score", 0.0))
        if "nsfw" in lbl or lbl in ["porn", "hentai", "sexy"]:
            return score >= threshold, res
    # no nsfw label found
    return False, res

# -------------------------
# Public analysis API (callable by FastAPI)
# -------------------------
def predict_api(image: Image.Image, text: str = ""):
    caption = generate_caption(image)
    similarity = clip_similarity(image, text or caption)
    combined_text = (text or "") + " . " + caption
    zres = run_zero_shot(combined_text)
    top_label = zres["labels"][0]
    top_score = float(zres["scores"][0])

    text_flagged, text_mod = moderate_text(text or caption)
    cap_flagged, cap_mod = moderate_text(caption)
    nsfw_flagged, nsfw_res = check_nsfw(image)

    unsafe = text_flagged or cap_flagged or nsfw_flagged
    allow = (not unsafe) and (similarity >= CLIP_SIM_THRESHOLD)

    category = top_label if top_score >= ZERO_SHOT_THRESHOLD else "Other"
    points = CATEGORY_POINTS.get(category, CATEGORY_POINTS["Other"]) if allow else 0

    return {
        "allow": bool(allow),
        "points": int(points),
        "message": "Accepted" if allow else ("Content violates community policy" if unsafe else "Low image-text similarity"),
        "caption": caption,
        "clip_similarity": float(similarity),
        "zero_shot_label": top_label,
        "zero_shot_score": float(top_score),
        "category": category,
        "moderation": {
            "text": text_mod,
            "caption": cap_mod,
            "nsfw": nsfw_res
        }
    }

# -------------------------
# Simulated DB (session) - Only initialize in Streamlit context
# -------------------------
def init_streamlit_session():
    """Initialize Streamlit session state."""
    if "users" not in st.session_state:
        st.session_state.users = {
            "test_user": {"points": 0, "posts": []}
        }

# -------------------------
# Streamlit UI
# -------------------------
# Only run UI code if in Streamlit context
username = None
api_base = os.getenv("MODEL_API_URL", "http://127.0.0.1:7000/analyze_post")

try:
    st.set_page_config(page_title="GreenPoints - AI Proof Analyzer", layout="wide")
    init_streamlit_session()
    
    st.title("🌱 GreenPoints — Image + Text Verifier (Prototype)")
    username = st.text_input("Username (demo):", value="test_user")
    if username not in st.session_state.users:
        st.session_state.users[username] = {"points": 0, "posts": []}

    st.subheader(f"Welcome, {username} — Points: {st.session_state.users[username]['points']}")

    # New: Upload or Take Photo (opens same Streamlit app in new tab)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Upload File", use_container_width=True):
            st.markdown("<script>window.open(window.location.href, '_blank');</script>", unsafe_allow_html=True)
    with col_b:
        if st.button("Take Photo", use_container_width=True):
            st.markdown("<script>window.open(window.location.href + '#camera', '_blank');</script>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Quick Submit (API-driven)")
    try:
        _secret_api_base = st.secrets.get("MODEL_API_URL")  # may raise if no secrets file
    except Exception:
        _secret_api_base = None
    api_base = os.getenv("MODEL_API_URL", _secret_api_base or "http://127.0.0.1:7000/analyze_post")

    # -------------------------
    # Streamlit UI Code (only runs in Streamlit context)
    # -------------------------
    tab_upload, tab_camera = st.tabs(["Upload Image", "Camera Capture"])  # keep theme consistent
    with tab_upload:
        with st.form("api_form_upload"):
            api_desc = st.text_area("Description", key="api_desc_u", height=100)
            api_file = st.file_uploader("Image (jpg/png)", type=["jpg", "jpeg", "png"], key="api_file_u")
            submit_api_u = st.form_submit_button("Analyze & Submit")
        if submit_api_u:
            if not api_file or not api_desc.strip():
                st.warning("Provide both image and description.")
            else:
                files = {"file": (api_file.name, api_file.getvalue(), api_file.type or "image/jpeg")}
                data = {"text": api_desc, "username": username}
                try:
                    resp = requests.post(api_base, files=files, data=data, timeout=120)
                    result = resp.json()
                    # Flask persistence service schema
                    if result.get("success") or ("updatedPoints" in result or "awardedPoints" in result):
                        awarded = int(result.get("awardedPoints", 0))
                        updated = result.get("updatedPoints", None)
                        category = result.get("category", "Other")
                        msg = f"✅ Accepted. You earned {awarded} points."
                        if updated is not None:
                            msg = f"✅ Accepted. You earned {awarded} points. Updated points: {updated}."
                        st.success(msg)
                        st.write("Category:", category)
                    # FastAPI direct schema fallback
                    elif result.get("allow") is not None:
                        if result.get("allow"):
                            st.success(f"✅ Accepted. You earned {int(result.get('points', 0))} points.")
                            st.write("Category:", result.get("category", "Other"))
                        else:
                            st.error("Content violates community policy")
                    else:
                        st.error(result.get("error") or result.get("message") or "Rejected")
                except Exception as e:
                    st.error(f"Analysis request failed: {e}")

    with tab_camera:
        camera_img = st.camera_input("Capture photo", key="api_cam")
        api_desc_c = st.text_area("Description", key="api_desc_c", height=100)
        if st.button("Analyze & Submit (Camera)"):
            if not camera_img or not api_desc_c.strip():
                st.warning("Provide both image and description.")
            else:
                files = {"file": (camera_img.name, camera_img.getvalue(), "image/jpeg")}
                data = {"text": api_desc_c, "username": username}
                try:
                    resp = requests.post(api_base, files=files, data=data, timeout=120)
                    result = resp.json()
                    if result.get("success") or ("updatedPoints" in result or "awardedPoints" in result):
                        awarded = int(result.get("awardedPoints", 0))
                        updated = result.get("updatedPoints", None)
                        category = result.get("category", "Other")
                        msg = f"✅ Accepted. You earned {awarded} points."
                        if updated is not None:
                            msg = f"✅ Accepted. You earned {awarded} points. Updated points: {updated}."
                        st.success(msg)
                        st.write("Category:", category)
                    elif result.get("allow") is not None:
                        if result.get("allow"):
                            st.success(f"✅ Accepted. You earned {int(result.get('points', 0))} points.")
                            st.write("Category:", result.get("category", "Other"))
                        else:
                            st.error("Content violates community policy")
                    else:
                        st.error(result.get("error") or result.get("message") or "Rejected")
                except Exception as e:
                    st.error(f"Analysis request failed: {e}")

    if username:  # Only show form if username is defined
        with st.form("submit_form", clear_on_submit=True):
            user_text = st.text_area("Describe your eco-friendly work (required):", height=120)
            uploaded = st.file_uploader("Upload image proof (jpg/png):", type=["jpg", "jpeg", "png"])
            submit = st.form_submit_button("Submit Proof")

        if submit:
            if not uploaded or not user_text.strip():
                st.warning("Please provide both image and description.")
            else:
                img = Image.open(uploaded).convert("RGB")
                ihash = img_hash_bytes(img)
                thash = text_hash(user_text)

                # duplicate checks
                existing_hashes = [p["img_hash"] for p in st.session_state.users[username]["posts"]]
                existing_text_hashes = [p["text_hash"] for p in st.session_state.users[username]["posts"]]

                if DUPLICATE_REJECT and (ihash in existing_hashes or thash in existing_text_hashes):
                    st.error("Duplicate post detected — this proof/text has already been submitted.")
                else:
                    with st.spinner("Analyzing image & text with AI models..."):
                        t0 = time.time()
                        # 1) Caption
                        caption = generate_caption(img)

                        # 2) CLIP similarity between user text and image
                        sim = clip_similarity(img, user_text)

                        # 3) Zero-shot classification on combined text (user text + caption)
                        combined = user_text + " . " + caption
                        zres = run_zero_shot(combined)
                        top_label = zres["labels"][0]
                        top_score = float(zres["scores"][0])

                        # 4) Moderation (text)
                        text_flagged, text_mod_items = moderate_text(user_text)

                        # 5) Moderation (caption)
                        cap_flagged, cap_mod_items = moderate_text(caption)

                        # 6) Image NSFW check (if available)
                        nsfw_flagged, nsfw_res = check_nsfw(img)

                        elapsed = time.time() - t0

                    # decision logic
                    if text_flagged or cap_flagged or nsfw_flagged:
                        # misuse
                        st.error("⚠️ Content flagged as unsafe/misuse. Points will be deducted and post rejected.")
                        st.write("Text moderation output:", text_mod_items)
                        st.write("Caption moderation output:", cap_mod_items)
                        st.write("NSFW image output (if available):", nsfw_res)
                        st.session_state.users[username]["points"] = max(0, st.session_state.users[username]["points"] - MISUSE_PENALTY)
                        st.session_state.users[username]["posts"].append({
                            "img_hash": ihash, "text_hash": thash, "status": "rejected_misuse",
                            "caption": caption, "clip_sim": sim, "z_label": top_label, "z_score": top_score,
                            "mod_text": text_mod_items, "nsfw": nsfw_res
                        })
                    else:
                        st.write(f"AI caption: **{caption}**")
                        st.write(f"CLIP similarity (image↔text): **{sim:.3f}** (threshold {CLIP_SIM_THRESHOLD})")
                        st.write(f"Category (zero-shot): **{top_label}** — score {top_score:.3f}")
                        st.write(f"Analysis time: {elapsed:.2f}s")

                        if sim < CLIP_SIM_THRESHOLD:
                            st.error("❌ The description does not match the image (low similarity). Post rejected.")
                            st.session_state.users[username]["posts"].append({
                                "img_hash": ihash, "text_hash": thash, "status": "rejected_no_match",
                                "caption": caption, "clip_sim": sim, "z_label": top_label, "z_score": top_score
                            })
                        else:
                            # award points: require reasonable zero-shot score, otherwise give 'Other'
                            if top_score >= ZERO_SHOT_THRESHOLD:
                                awarded_category = top_label
                            else:
                                awarded_category = "Other"

                            points = CATEGORY_POINTS.get(awarded_category, CATEGORY_POINTS["Other"])
                            # optional: small scaling by confidence
                            # points = int(points * (0.8 + 0.4 * min(sim, 0.6)))  # commented: keep full points
                            st.success(f"✅ Post accepted! Category: **{awarded_category}** — you earned **{points}** points.")
                            st.session_state.users[username]["points"] += points
                            st.session_state.users[username]["posts"].append({
                                "img_hash": ihash, "text_hash": thash, "status": "accepted",
                                "caption": caption, "clip_sim": sim, "z_label": top_label, "z_score": top_score,
                                "category": awarded_category, "points": points
                            })

    # -------------------------
    # Show feed & leaderboard (basic) - Only in Streamlit context
    # -------------------------
    if username:  # Only show feed if username is defined
        st.markdown("---")
        st.header("Community Feed (your posts)")
        posts = st.session_state.users[username]["posts"][::-1]  # newest first
        if not posts:
            st.info("No posts yet.")
        else:
            for p in posts[:50]:
                st.write(f"**Status:** {p.get('status','n/a')} | **Category:** {p.get('category','-')} | **Points:** {p.get('points','-')}")
                st.write(f"**Caption:** {p.get('caption','-')}")
                clip_sim = p.get('clip_sim', '-')
                if isinstance(clip_sim, (int, float)):
                    st.write(f"CLIP sim: {clip_sim:.3f} | Zero-shot: {p.get('z_label','-')} ({p.get('z_score','-'):.3f})")
                else:
                    st.write(f"CLIP sim: {clip_sim} | Zero-shot: {p.get('z_label','-')} ({p.get('z_score','-'):.3f})")
                st.write("---")

        # Basic leaderboard (session only)
        st.header("Leaderboard (session)")
        leader = sorted(st.session_state.users.items(), key=lambda kv: kv[1]["points"], reverse=True)
        for uname, info in leader:
            st.write(f"**{uname}** — {info['points']} pts")

except (NameError, AttributeError):
    # Not in Streamlit context - this is OK for API usage
    pass

def predict(image_path):
    """CLI function to predict from image path. Requires PIL Image."""
    from PIL import Image
    img = Image.open(image_path).convert("RGB")
    result = predict_api(img, "")
    print(json.dumps(result))
    return result

# Skip CLI execution when run via Streamlit
if __name__ == "__main__":
    # Check if running as Streamlit app
    try:
        import streamlit.web.cli as stcli
        # If we can import streamlit CLI, we're likely in Streamlit context
        # Streamlit will handle execution, so we don't need to do anything here
        pass
    except ImportError:
        # Not in Streamlit context - could be CLI mode
        if len(sys.argv) > 1:
            image_path = sys.argv[1]
            # For CLI, we need to load models differently or use API
            print("CLI mode: Use the API endpoint or run via Streamlit instead.")
            print(f"Example: streamlit run {__file__}")
        else:
            # No CLI args - this is meant to be run via Streamlit
            print("This script is designed to run via Streamlit.")
            print(f"Run with: streamlit run {__file__}")
