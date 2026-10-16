import streamlit as st
import subprocess
import numpy as np
import re
from pathlib import Path
from faster_whisper import WhisperModel

st.set_page_config(page_title="Auto Shorts Maker", page_icon="🎬")
st.title("🎬 Long Video to Shorts Generator")
st.write("ইউটিউব ভিডিওর লিংক দিন, আমরা অটোমেটিক শর্টস বানিয়ে দেব।")

# সাইডবার সেটিংস
st.sidebar.header("সেটিংস")
video_url = st.sidebar.text_input("YouTube Video URL:")
num_clips = st.sidebar.slider("কতটি শর্টস চান?", 1, 10, 3)
min_sec = st.sidebar.number_input("সর্বনিম্ন সেকেন্ড:", value=4.0)
max_sec = st.sidebar.number_input("সর্বোচ্চ সেকেন্ড:", value=30.0)

if st.sidebar.button("শর্টস তৈরি করুন 🚀"):
    if not video_url:
        st.error("অনুগ্রহ করে একটি ইউটিউব লিংক দিন!")
    else:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        with st.spinner("১/৫: ভিডিও ডাউনলোড হচ্ছে..."):
            video_path = output_dir / "video.mp4"
            subprocess.run(["yt-dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]", "-o", str(video_path), video_url], check=True)
        
        with st.spinner("২/৫: অডিও আলাদা করা হচ্ছে..."):
            audio_path = output_dir / "audio.wav"
            subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(audio_path)], check=True, capture_output=True)
        
        with st.spinner("৩/৫: ট্রান্সক্রিপশন হচ্ছে..."):
            model = WhisperModel("base", device="cpu", compute_type="auto") 
            segments, info = model.transcribe(str(audio_path), beam_size=5, language="bn")
            transcribed_data = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
        
        with st.spinner("৪/৫: স্কোরিং হচ্ছে..."):
            all_windows = []
            cur = []
            for i, w in enumerate(transcribed_data):
                if len(cur) > 0 and (w["start"] - cur[0]["start"] >= min_sec or i == len(transcribed_data) - 1):
                    if len(cur) > 0:
                        text = " ".join([x["text"] for x in cur])
                        dur = cur[-1]["end"] - cur[0]["start"]
                        if dur > 0:
                            score = len(text.split()) / dur + (text.count("?") + text.count("!")) * 0.5
                            if min_sec <= dur <= max_sec:
                                all_windows.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": text, "score": score})
                    cur = []
                cur.append(w)
            chosen_clips = sorted(all_windows, key=lambda x: x["score"], reverse=True)[:num_clips]
            chosen_clips = sorted(chosen_clips, key=lambda x: x["start"])
        
        with st.spinner("৫/৫: ফাইল তৈরি হচ্ছে..."):
            for n, clip in enumerate(chosen_clips, 1):
                st_val = clip["start"]
                et_val = clip["end"]
                
                clip_path = output_dir / f"short_{n}.mp4"
                subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-ss", str(st_val), "-to", str(et_val), "-vf", "crop=ih*9/16:ih", "-c:a", "copy", str(clip_path)], check=True, capture_output=True)
                
                with open(output_dir / f"short_{n}_info.txt", "w", encoding="utf-8") as f:
                    f.write(f"সময়: {int(st_val//60)}:{int(st_val%60)} - {int(et_val//60)}:{int(et_val%60)}\nস্কোর: {clip['score']:.2f}\nটেক্সট: {clip['text']}\n")
                
                # ডাউনলোড বাটন
                with open(clip_path, "rb") as file:
                    st.download_button(label=f"⬇️ ডাউনলোড short_{n}.mp4", data=file, file_name=f"short_{n}.mp4", mime="video/mp4")
        
        st.success("✅ সব শর্টস তৈরি হয়ে গেছে!")
