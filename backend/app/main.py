from fastapi import FastAPI, UploadFile, File, Form
import shutil
import whisper
import os
from difflib import SequenceMatcher

app = FastAPI()

# Load Whisper model once at startup
model = whisper.load_model("base")  
# Options: tiny (fast), base (balanced), small (better)


@app.get("/")
def root():
    return {"status": "Backend running"}


@app.post("/check-pronunciation")
async def check_pronunciation(
    audio: UploadFile = File(...),
    word: str = Form(...)
):
    # Save uploaded file
    file_location = f"temp_{audio.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    # Transcribe audio using Whisper
    result = model.transcribe(file_location)
    spoken_text = result["text"].strip().lower()

    expected_word = word.lower()

    # Compare spoken vs expected
    similarity = SequenceMatcher(None, spoken_text, expected_word).ratio()
    score = int(similarity * 100)

    # Clean temp file
    os.remove(file_location)

    return {
        "expected": expected_word,
        "spoken": spoken_text,
        "score": score
    }
