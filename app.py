"""Streamlit web UI for the brainrot video generator."""

import tempfile
from pathlib import Path

import streamlit as st

from src.backgrounds import BACKGROUND_STYLES, DEFAULT_BACKGROUND_STYLE
from src.config import VideoConfig
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

    words_per_group = st.slider(
        "Words per caption group",
        min_value=2,
        max_value=8,
        value=4,
        help="How many words appear on screen at once.",
    )

    st.markdown("---")
    st.markdown("### Background")

    bg_style = st.selectbox(
        "Background Style",
        options=list(BACKGROUND_STYLES.keys()),
        index=list(BACKGROUND_STYLES.keys()).index(DEFAULT_BACKGROUND_STYLE),
        format_func=lambda k: f"{k.replace('_', ' ').title()} — {BACKGROUND_STYLES[k]}",
        help="Choose a procedural background style for your video.",
    )

    st.markdown("**— OR —**")
    bg_file = st.file_uploader(
        "Upload your own background clip",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        help=(
            "Upload Subway Surfer, Minecraft parkour, or any gameplay clip."
            " Overrides the style above."
        ),
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
            words_per_group=words_per_group,
        )

        with st.spinner("Generating your brainrot video... This may take a minute."):
            progress = st.progress(0, text="Generating TTS audio...")

            try:
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
    "Built with edge-tts, moviepy, and Streamlit"
    "</div>",
    unsafe_allow_html=True,
)
