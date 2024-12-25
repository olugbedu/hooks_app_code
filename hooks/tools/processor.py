import logging
import os
import subprocess
import threading

from tqdm import tqdm
import pandas as pd
from moviepy.editor import AudioFileClip

from django.core.cache import cache
from django.http import JsonResponse

from hooks.models import Hook

from .utils import hex_to_rgb, handle_task_cancellation, delete_temp_dir
from .spreadsheet_extractor import fetch_google_sheet_data, extract_word_color_data
from .audio_processors import process_audios
from .video_processors import process_audio_on_videos

from hooks.models import Task

logging.basicConfig(level=logging.DEBUG)
canceled_tasks = set()

def process(params):
  task_id = params.get('task_id', None)
  try:
    input_df = params['input_df']
    if 'Hook Text' not in input_df.columns:
      raise Exception("The column 'Hook Text' does not exist in the DataFrame.")

    google_sheet_link = params.get('google_sheet_link')
    if not google_sheet_link:
      raise Exception("Missing 'google_sheet_link' in params.")

    word_color_data = extract_word_color_data(google_sheet_link)

    for idx, row in input_df.iterrows():
      hook_text = row['Hook Text']

    ELEVENLABS_API_KEY = params['api_key']
    no_of_parallel_executions = params['parallel_processing']

    INPUT_DIR = params['input_dir']
    OUTPUT_DIR = params['output_dir']
    voice_id = params['voice_id']
    temp_dir = params['temp_dir']
    top_box_color = params['top_box_color']
    default_text_color = params['default_text_color']

    input_videos_folder = os.path.join(INPUT_DIR, 'video')
    output_audios_folder = os.path.join(OUTPUT_DIR, 'audios')
    output_videos_folder = os.path.join(OUTPUT_DIR, 'videos')
    is_tiktok = 0
    if params['aspect_ratio'] == 'option1':
      OUT_VIDEO_DIM = "1080x1080"
    elif params['aspect_ratio'] == 'option2':
      OUT_VIDEO_DIM = "1080x1350"
    elif params['aspect_ratio'] == 'option3':
      OUT_VIDEO_DIM = "1080x1920"
      is_tiktok = 1
    elif params['aspect_ratio'] == 'option4':
      OUT_VIDEO_DIM = "1920x1080"
    else:
      raise ValueError(f"Unsupported aspect ratio: {params['aspect_ratio']}")

    OUT_VIDEO_HEIGHT = int(OUT_VIDEO_DIM.split('x')[1])
    OUT_VIDEO_WIDTH = int(OUT_VIDEO_DIM.split('x')[0])

    if len(os.listdir(input_videos_folder)) == 0:
      raise Exception(
        f"input/videos folder {input_videos_folder} does not contain any videos"
      )
    video_files = sorted(
      [
        f for f in os.listdir(input_videos_folder)
        if f.endswith('.mp4') or f.endswith('.mov')
      ]
    )

    for col in ["Hook Video Filename", "Input Video Filename", "Audio Filename",
                "Voice"]:
      if col not in input_df.columns:
        input_df[col] = ''

    l_unprocessed_rows = len(input_df[input_df['Hook Video Filename'] == ''])

    all_hooks = []
    total_rows = len(input_df)
    current_row = 0

    for idx_1, row in tqdm(input_df.iterrows(), total=total_rows,
                           desc="Processing rows"):
      hook_text = row['Hook Text']
      hook_number = idx_1 + 1

      process_audios(
        ELEVENLABS_API_KEY, row, hook_number, hook_text, input_df, idx_1,
        output_audios_folder, voice_id
      )
      logging.info('Audio proccessed successfully')

    current_thread_count = 0

    for idx, row in tqdm(input_df.iterrows(), total=total_rows,
                         desc="Processing rows"):
      hook_text = row['Hook Text']
      hook_number = idx + 1

      audio_clip = AudioFileClip(
        os.path.join(output_audios_folder, row['Audio Filename'])
      )
      video_index = idx % len(video_files)
      num_videos_to_use = int(round(audio_clip.duration / 2))

      video_file_size = len(video_files)
      if num_videos_to_use + video_index > video_file_size:
        num_videos_to_use = video_file_size - video_index

      last_video = video_index + num_videos_to_use
      video_files_to_use = [
        os.path.join(input_videos_folder, video_files[i])
        for i in range(video_index, last_video)
      ]

      if params['task_id'] in canceled_tasks:
        return handle_task_cancellation(temp_dir, task_id)

      hook_job = threading.Thread(
        target=process_audio_on_videos,
        args=(
          row, video_files_to_use, idx, input_df, hook_number, hook_text,
          num_videos_to_use, audio_clip, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT,
          output_videos_folder, total_rows, task_id, top_box_color,
          default_text_color, word_color_data, None, params['add_watermark'],
          is_tiktok
        )
      )
      hook_job.start()
      all_hooks.append(hook_job)
      current_thread_count += 1
      if current_thread_count == int(no_of_parallel_executions):
        for hook in all_hooks:
          hook.join()
        all_hooks.clear()
        current_thread_count = 0
    for hook in all_hooks:
      try:
        hook.join()
      except Exception as err:
        logging.error(f'failed to join all hooks --> {str(err)}')

    # Now generate the video links after all processing is complete
    credits_used = 0
    video_links = []
    for idx, row in input_df.iterrows():
      logging.info('Trying to generate link')
      row['Hook Video Filename'] = f'hook_{idx}.mp4'
      video_path = os.path.join(
        output_videos_folder, row['Hook Video Filename']
      )
      video_links.append(
        {
          'file_name': row['Hook Video Filename'],
          'video_link': video_path
        }
      )
      credits_used += 1
      logging.info("used one credit")
      logging.info(
        f"Generated video link with file name: {row['Hook Video Filename']}"
      )

    logging.info(f"Task {task_id} completed.")
    return video_links, credits_used

  except Exception as e:
    logging.error(f"Error during processing ---> {str(e)}")
    delete_temp_dir(params.get('temp_dir', ''))

def process_files(
  temp_dir, task_id, add_watermark=False, aspect_ratio='option1'
):

  hook_object = Hook.objects.filter(task_id=task_id).first()
  if not hook_object:
    return JsonResponse({"error": "Invalid Task id"})

  # Extract necessary fields from the object
  video_files = hook_object.hooks_content
  google_sheet_link = hook_object.google_sheets_link
  voice_id = hook_object.voice_id
  api_key = hook_object.eleven_labs_api_key
  parallel_processing = hook_object.parallel_processing
  top_box_color_value = hook_object.box_color
  main_box_color_value = hook_object.font_color

  # Convert hex colors to RGB
  top_box_color = hex_to_rgb(top_box_color_value)
  default_text_color = hex_to_rgb(main_box_color_value)

  if not video_files or not google_sheet_link or not voice_id or not api_key or not parallel_processing:
    return JsonResponse({"error": "Missing form data"})

  # Create directories for input/output files
  input_videos_folder = os.path.join(temp_dir, 'input', 'video')
  output_audios_folder = os.path.join(temp_dir, 'output', 'audios')
  output_videos_folder = os.path.join(temp_dir, 'output', 'videos')

  # Ensure the directories exist
  os.makedirs(input_videos_folder, exist_ok=True)
  os.makedirs(output_audios_folder, exist_ok=True)
  os.makedirs(output_videos_folder, exist_ok=True)

  # Save the video file
  video_files_paths = []
  video_file_name = os.path.basename(video_files.name)
  video_file_path = os.path.join(input_videos_folder, video_file_name)
  os.makedirs(os.path.dirname(video_file_path), exist_ok=True)
  with open(video_file_path, 'wb+') as destination:
    for chunk in video_files.chunks():
      destination.write(chunk)
  video_files_paths.append(video_file_path)

  # Fetch the data from Google Sheets
  google_sheet_data = fetch_google_sheet_data(google_sheet_link)
  extract_word_color_data(google_sheet_link)
  input_df = pd.DataFrame(google_sheet_data)
  if input_df.empty or ('Hook Text' not in input_df.columns
                        and input_df.shape[1] > 0):
    if input_df.shape[1] == 1:
      input_df.columns = ['Hook Text']
    else:
      return JsonResponse(
        {
          "error":
            "Ensure the google sheet access is updated to anyone with link."
        }
      )

  # Create a params dictionary to pass to the background task
  params = {
    "input_dir": os.path.join(temp_dir, 'input'),
    "output_dir": os.path.join(temp_dir, 'output'),
    "video_files_paths": video_files_paths,
    "voice_id": voice_id,
    "api_key": api_key,
    "parallel_processing": parallel_processing,
    "task_id": task_id,
    "temp_dir": temp_dir,
    "top_box_color": top_box_color,
    "default_text_color": default_text_color,
    "input_df": input_df,
    "google_sheet_link": google_sheet_link,
    "add_watermark": add_watermark,
    "aspect_ratio": aspect_ratio,
  }
  cache.set(task_id, temp_dir, timeout=600)

  video_links, credits_used = process(params)
  return video_links, credits_used
