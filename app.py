"""Streamlit web UI for the brainrot video generator."""

import tempfile
from pathlib import Path

import streamlit as st

from src.backgrounds import BACKGROUND_STYLES, DEFAULT_BACKGROUND_STYLE
from src.config import CAPTION_STYLES, DEFAULT_CAPTION_STYLE, VideoConfig
from src.video import generate_video

st.set_page_config(
    page_title="Brainrot Generator",
    page_icon="🧠",
    layout="centered",
)

st.title("🧠 Brainrot Generator")
st.markdown("*Turn any text into an informative brainrot-style short-form video*")

# --- Sidebar settings ---
with st.sidebar:
    st.header("Settings")

    voice = st.selectbox(
        "TTS Voice",
        options=[
            "en-US-ChristopherNeural",
            "en-US-AriaNeural",
            "en-US-GuyNeural",
            "en-US-JennyNeural",
            "en-US-EricNeural",
            "en-US-SteffanNeural",
            "en-GB-RyanNeural",
            "en-GB-SoniaNeural",
            "en-AU-WilliamNeural",
            "en-AU-NatashaNeural",
        ],
        index=0,
        help="Select the TTS voice for narration.",
    )

    rate = st.select_slider(
        "Speech Rate",
        options=["-20%", "-10%", "+0%", "+10%", "+20%", "+30%", "+50%"],
        value="+10%",
        help="Faster = more brainrot energy.",
    )

    st.markdown("---")
    st.markdown("### Caption Style")

    caption_style = st.selectbox(
        "Caption Preset",
        options=list(CAPTION_STYLES.keys()),
        index=list(CAPTION_STYLES.keys()).index(DEFAULT_CAPTION_STYLE),
        format_func=lambda k: f"{k.replace('_', ' ').title()} — {CAPTION_STYLES[k]['description']}",
        help="Choose how captions are rendered on the video.",
    )

    words_per_group = st.slider(
        "Words per caption group",
        min_value=1,
        max_value=8,
        value=CAPTION_STYLES[caption_style]["words_per_group"],
        help="How many words appear on screen at once. Auto-set by style preset.",
    )

    st.markdown("---")
    st.markdown("### Background")

    bg_mode = st.radio(
        "Background Mode",
        options=["stock_footage", "procedural", "custom_upload"],
        format_func=lambda x: {
            "stock_footage": "📸 Stock Footage (matches your text)",
            "procedural": "🎨 Procedural Animation",
            "custom_upload": "📁 Upload Custom Video",
        }[x],
        index=0,
        help="Choose how the background visuals are generated.",
    )

    bg_style = DEFAULT_BACKGROUND_STYLE
    bg_file = None
    scene_change_words = 15
    crossfade_duration = 0.5

    if bg_mode == "procedural":
        bg_style = st.selectbox(
            "Background Style",
            options=list(BACKGROUND_STYLES.keys()),
            index=list(BACKGROUND_STYLES.keys()).index(DEFAULT_BACKGROUND_STYLE),
            format_func=lambda k: f"{k.replace('_', ' ').title()} — {BACKGROUND_STYLES[k]}",
            help="Choose a procedural background style for your video.",
        )
    elif bg_mode == "custom_upload":
        bg_file = st.file_uploader(
            "Upload your own background clip",
            type=["mp4", "mov", "avi", "mkv", "webm"],
            help=(
                "Upload Subway Surfer, Minecraft parkour, or any gameplay clip."
            ),
        )
    else:
        st.info(
            "🔍 Stock footage will be fetched from Pexels based on your text content. "
            "Visuals change per sentence to match the narration. "
            "Requires PEXELS_API_KEY environment variable."
        )
        scene_change_words = st.slider(
            "Words per scene",
            min_value=8,
            max_value=30,
            value=15,
            help="How often the background visual changes. Lower = more frequent cuts.",
        )
        crossfade_duration = st.slider(
            "Crossfade duration (seconds)",
            min_value=0.0,
            max_value=2.0,
            value=0.5,
            step=0.1,
            help="Smooth transition between scenes. 0 = hard cut.",
        )

# --- Main content ---
text = st.text_area(
    "Enter your text",
    height=200,
    placeholder=(
        "Paste the informative text you want to turn into a brainrot video.\n\n"
        "Example: The mitochondria is the powerhouse of the cell. "
        "It generates most of the cell's supply of adenosine triphosphate, "
        "used as a source of chemical energy..."
    ),
)

if st.button("🎬 Generate Video", type="primary", use_container_width=True):
    if not text.strip():
        st.error("Please enter some text first!")
    else:
        # Save uploaded background if provided
        bg_path = None
        if bg_file is not None:
            bg_tmp = tempfile.NamedTemporaryFile(
                suffix=f".{bg_file.name.split('.')[-1]}", delete=False
            )
            bg_tmp.write(bg_file.read())
            bg_tmp.close()
            bg_path = bg_tmp.name

        config = VideoConfig(
            text=text.strip(),
            voice=voice,
            rate=rate,
            background_video=bg_path,
            background_style=bg_style,
            use_stock_footage=(bg_mode == "stock_footage"),
            caption_style=caption_style,
            words_per_group=words_per_group,
            scene_change_words=scene_change_words,
            crossfade_duration=crossfade_duration,
        )

        with st.spinner("Generating your brainrot video... This may take a minute."):
            progress = st.progress(0, text="Generating TTS audio...")

            try:
                if config.use_stock_footage:
                    progress.progress(10, text="Generating TTS audio...")
                else:
                    progress.progress(20, text="Generating TTS audio...")

                output_path = generate_video(config)
                progress.progress(100, text="Done!")

                st.success("Video generated!")

                # Display the video
                video_bytes = Path(output_path).read_bytes()
                st.video(video_bytes)

                # Download button
                st.download_button(
                    label="⬇️ Download Video",
                    data=video_bytes,
                    file_name="brainrot_output.mp4",
                    mime="video/mp4",
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"Error generating video: {e}")
                raise

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; font-size: 0.8em;'>"
    "Built with edge-tts, moviepy, Pexels, and Streamlit"
    "</div>",
    unsafe_allow_html=True,
)
