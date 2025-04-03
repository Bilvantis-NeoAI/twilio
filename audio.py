import whisper

# Load the Whisper model (you can use "tiny", "base", "small", "medium", "large")
model = whisper.load_model("base")

# Transcribe an audio file
result = model.transcribe("your_audio_file.mp3")

# Print the transcription
print(result["text"])
