# Step1: Record audio from microphone

# dependencies: ffmpeg, portaudio, pyaudio (commands available in description)
import os
import glob
import logging
import shutil
from io import BytesIO

from dotenv import load_dotenv
import speech_recognition as sr


load_dotenv()


def _configure_ffmpeg_path():
    ffmpeg_binary = os.environ.get("FFMPEG_BINARY")
    ffmpeg_dir = os.environ.get("FFMPEG_DIR")

    candidates = []
    if ffmpeg_binary:
        candidates.append(ffmpeg_binary)
    if ffmpeg_dir:
        candidates.append(os.path.join(ffmpeg_dir, "ffmpeg.exe"))

    resolved = shutil.which("ffmpeg")
    if resolved:
        candidates.append(resolved)

    onedrive_root = os.environ.get("OneDriveCommercial") or os.environ.get("OneDrive")
    if onedrive_root:
        candidates.extend(
            glob.glob(
                os.path.join(onedrive_root, "ffmpeg-*", "**", "bin", "ffmpeg.exe"),
                recursive=True,
            )
        )

    candidates.extend(
        glob.glob(os.path.join(os.environ.get("USERPROFILE", ""), "ffmpeg-*", "**", "bin", "ffmpeg.exe"), recursive=True)
    )

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            ffmpeg_folder = os.path.dirname(candidate)
            current_path = os.environ.get("PATH", "")
            if ffmpeg_folder not in current_path.split(os.pathsep):
                os.environ["PATH"] = ffmpeg_folder + os.pathsep + current_path
            return candidate
    return None


FFMPEG_BINARY = _configure_ffmpeg_path()

from pydub import AudioSegment

if FFMPEG_BINARY:
    AudioSegment.converter = FFMPEG_BINARY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

def record_audio(file_path, timeout=20, phrase_time_limit=None):
    """
    Simplified function to record audio from the microphone and save it as an MP3 file.

    Args:
    file_path (str): Path to save the recorded audio file.
    timeout (int): Maximum time to wait for a phrase to start (in seconds).
    phrase_time_lfimit (int): Maximum time for the phrase to be recorded (in seconds).
    """
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        logging.info("Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        logging.info("Start speaking now...")

        try:
            # Record the audio
            audio_data = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            logging.warning("No speech detected before timeout.")
            return None

        logging.info("Recording complete.")

        # Convert the recorded audio to an MP3 file
        wav_data = audio_data.get_wav_data()
        audio_segment = AudioSegment.from_wav(BytesIO(wav_data))
        audio_segment.export(file_path, format="mp3", bitrate="128k")

        logging.info(f"Audio saved to {file_path}")
        return file_path

audio_filepath="patient_voice_test.mp3"
#record_audio(audio_filepath, timeout=20, phrase_time_limit=10)


# Step2: Convert audio to text
from groq import Groq

def transcribe_patient_voice(audio_filepath):
    groq_api_key = os.environ.get("GROQ_API_KEY")

    client = Groq(api_key=groq_api_key)
    with open(audio_filepath, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model=os.environ.get("WHISPER_MODEL", "whisper-large-v3"),
        )

    return transcription.text


if __name__ == "__main__":
    logging.info("Running microphone capture test...")
    recorded_file = record_audio(audio_filepath, timeout=20, phrase_time_limit=10)

    if not recorded_file and os.path.exists(audio_filepath):
        logging.info("Using existing audio file for transcription test: %s", audio_filepath)
        recorded_file = audio_filepath

    if recorded_file:
        try:
            transcript = transcribe_patient_voice(recorded_file)
            logging.info("Transcription output: %s", transcript)
        except Exception:
            logging.exception("Transcription test failed.")