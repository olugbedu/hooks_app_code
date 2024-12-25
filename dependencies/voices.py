from elevenlabs import VoiceSettings

# Define a default voice setting for most voices
default_voice_setting = VoiceSettings(
    stability=0.5,
    similarity_boost=0.75,
    style=0.0,
    use_speaker_boost=True
)

# Dictionary to store voice settings for different voices
VOICE_SETTINGS = {
    # Bradley has a unique setting
    "Bradley - Formal and Serious": VoiceSettings(
        stability=1,
        similarity_boost=1,
        style=0.0,
        use_speaker_boost=True
    ),
    # Other voices use the default settings
    "Daniel": default_voice_setting,
    "Brian": default_voice_setting,
    "Charlie": default_voice_setting,
    "Drew": default_voice_setting,
    "James": default_voice_setting,
    "Joseph": default_voice_setting,
    "Micheal": default_voice_setting,
    "Paul": default_voice_setting,
    "Thomas": default_voice_setting,
    "Domi": default_voice_setting,
    "Dorothy": default_voice_setting,
    "Emily": default_voice_setting,
    "Matilda": default_voice_setting,
    "Serena": default_voice_setting
}