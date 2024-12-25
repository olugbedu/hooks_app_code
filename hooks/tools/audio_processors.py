# Utility functions used to process audios
import os
import re
import requests
import logging

logging.basicConfig(level=logging.DEBUG)

def text_to_speech_file(api_key, text: str, save_file_path: str, voice_id: str, remove_punctuation: bool = True) -> bool:
    if remove_punctuation:
        text = text.replace('-', ' ').replace('"', ' ').replace("'", ' ')
        text = re.sub(r'[^\w\s]', '', text)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        logging.error(f"API request failed with status code {response.status_code}: {response.text}")
        raise Exception(f"API request failed with status code {response.status_code}")

    with open(save_file_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return True, voice_id

def process_audios(api_key, row, hook_number, hook_text, input_df, idx, output_audios_folder, voice_id):
    print(voice_id)
    if row['Audio Filename'] in (None, '') or not os.path.exists(os.path.join(output_audios_folder, row['Audio Filename'])):
        logging.info(f"Generating voiceover for hook {hook_number}...")
        audio_filename = os.path.join(output_audios_folder, f'hook_{hook_number}.mp3')
        # import pdb;pdb.set_trace()
        try:
            status, voice_name = text_to_speech_file(api_key, hook_text, audio_filename, voice_id)
            row['Voice'] = voice_name
            row['Audio Filename'] = os.path.basename(audio_filename)
            input_df.at[idx, 'Voice'] = voice_name
            input_df.at[idx, 'Audio Filename'] = row['Audio Filename']
        except Exception as err:
            logging.error(f"Failed to hook audio file --> {audio_filename} --> {str(err)}", exc_info=True)
