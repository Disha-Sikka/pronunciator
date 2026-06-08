from fastapi import FastAPI, UploadFile, File, Form
import shutil
import whisper
import os
from difflib import SequenceMatcher
import eng_to_ipa as ipa

app = FastAPI()

# Load Whisper model once at startup
model = whisper.load_model("base")


@app.get("/")
def root():
    return {"status": "Backend running"}


def get_phonemes(word: str) -> str:
    """Convert a word to IPA phonemes."""
    result = ipa.convert(word)
    return result


def phoneme_score(expected_word: str, spoken_word: str) -> tuple[int, list[str]]:
    """
    Compare phonemes of expected vs spoken word.
    Returns a score (0-100) and a list of feedback tips.
    """
    expected_ipa = get_phonemes(expected_word)
    spoken_ipa = get_phonemes(spoken_word)

    tips = []

    # If IPA conversion failed (word not in dictionary), fall back to text similarity
    if "*" in expected_ipa or "*" in spoken_ipa:
        similarity = SequenceMatcher(None, expected_word, spoken_word).ratio()
        return int(similarity * 100), ["Could not find phoneme data for this word. Showing text similarity score."]

    # Phoneme-level similarity
    similarity = SequenceMatcher(None, expected_ipa, spoken_ipa).ratio()
    score = int(similarity * 100)

    # Generate specific feedback by comparing phonemes character by character
    expected_phones = list(expected_ipa.replace("ˈ", "").replace("ˌ", ""))
    spoken_phones = list(spoken_ipa.replace("ˈ", "").replace("ˌ", ""))

    # Find missing or wrong sounds
    missing = set(expected_phones) - set(spoken_phones)
    extra = set(spoken_phones) - set(expected_phones)

    # Common phoneme tips
    phoneme_tips = {
        "θ": "TH sound — put your tongue between your teeth and blow air",
        "ð": "TH sound (voiced) — like 'the', tongue between teeth, vibrate vocal cords",
        "ŋ": "NG sound — back of tongue touches roof of mouth (like 'sing')",
        "ʃ": "SH sound — lips slightly forward (like 'shoe')",
        "ʒ": "ZH sound — like the 's' in 'measure'",
        "tʃ": "CH sound — like 'chair'",
        "dʒ": "DJ sound — like 'judge'",
        "æ": "Short A — mouth wide open, tongue low (like 'cat')",
        "ɪ": "Short I — relaxed, quick (like 'bit')",
        "ʊ": "Short OO — lips rounded but relaxed (like 'book')",
        "ɛ": "Short E — mouth slightly open (like 'bed')",
        "ɑ": "AH sound — mouth wide open (like 'father')",
        "ɔ": "AW sound — lips rounded (like 'thought')",
        "ə": "Schwa — unstressed, relaxed 'uh' sound",
        "r": "R sound — tongue curls back slightly, don't touch roof of mouth",
        "l": "L sound — tongue tip touches just behind upper front teeth",
        "v": "V sound — upper teeth touch lower lip, vibrate",
        "w": "W sound — lips rounded, then open quickly",
    }

    for phoneme in missing:
        if phoneme in phoneme_tips:
            tips.append(f"Missing '{phoneme}' sound: {phoneme_tips[phoneme]}")

    if not tips and score < 90:
        tips.append("Close! Focus on matching the rhythm and stress of the word.")

    if score >= 90:
        tips.append("Excellent pronunciation! 🎉")

    return score, tips


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

    # Clean up punctuation from Whisper output
    spoken_word = spoken_text.strip(".,!?").split()[0] if spoken_text else ""
    expected_word = word.lower().strip()

    # Get IPA for display
    expected_ipa = get_phonemes(expected_word)
    spoken_ipa = get_phonemes(spoken_word) if spoken_word else ""

    # Calculate phoneme score
    score, tips = phoneme_score(expected_word, spoken_word)

    # Clean temp file
    os.remove(file_location)

    return {
        "expected": expected_word,
        "spoken": spoken_text,
        "expected_ipa": expected_ipa,
        "spoken_ipa": spoken_ipa,
        "score": score,
        "tips": tips
    }