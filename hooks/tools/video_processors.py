# Utility functions used in video processing
import logging
import os
import re
import shutil
from moviepy.editor import VideoFileClip, TextClip, ColorClip, CompositeVideoClip, ImageClip, concatenate_videoclips
from moviepy.video.fx.all import crop
from .utils import split_hook_text
from .font_utils import setup_fontconfig
import numpy as np
from django.conf import settings

logging.basicConfig(level=logging.DEBUG)

def crop_to_aspect_ratio(video_clip, target_width, target_height):
  original_width, original_height = video_clip.size
  target_aspect_ratio = target_width / target_height
  original_aspect_ratio = original_width / original_height

  if original_aspect_ratio > target_aspect_ratio:
    # Crop width to match the target aspect ratio
    new_width = int(target_aspect_ratio * original_height)
    x_center = original_width / 2
    x1 = int(x_center - new_width/2)
    x2 = int(x_center + new_width/2)
    y1, y2 = 0, original_height
  else:
    # Crop height to match the target aspect ratio
    new_height = int(original_width / target_aspect_ratio)
    y_center = original_height / 2
    y1 = int(y_center - new_height/2)
    y2 = int(y_center + new_height/2)
    x1, x2 = 0, original_width

  # Crop the video to the desired aspect ratio
  cropped_clip = crop(video_clip, x1=x1, y1=y1, x2=x2, y2=y2)

  # If the cropped video is not the exact target size, resize without distorting the video
  if cropped_clip.size != (target_width, target_height):
    cropped_clip = cropped_clip.resize((target_width, target_height))

  return cropped_clip

def create_custom_text_clip(
  hook_text, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, top_box_color, text_color,
  font_size, word_color_data, is_tiktok
):
  try:
    orig_hook_text_parts = split_hook_text(hook_text)
    hook_text = ' '.join(
      [word['text'] for cell in word_color_data for word in cell]
    )
    hook_text_parts = split_hook_text(hook_text)
    logging.info(f"Hook text parts: {hook_text_parts}")
    x_multiplier = OUT_VIDEO_WIDTH / 360
    y_multiplier = OUT_VIDEO_HEIGHT / 450
    min_red_area_h = int(round(40 * y_multiplier))
    fontsize1 = int(round(15 * x_multiplier))
    if is_tiktok == 1:
      fontsize1 += 18
    if OUT_VIDEO_WIDTH == 1920 and OUT_VIDEO_HEIGHT == 1080:
      fontsize1 -= 20

    max_width = OUT_VIDEO_WIDTH - 100
    logging.info(f'Variables created successfully')
    x_margin = 5

    # Setup Fontconfig for custom font
    font_path = os.path.abspath(
      str(settings.BASE_DIR) + '/dependencies/fonts/mu.otf'
    )
    logging.info(f"Font path: {font_path}")
    temp_fontconfig_dir = setup_fontconfig(font_path)

    # Build Pango-formatted text string with color for each word for the first part only
    pango_text = ""
    word_index = 0
    char_index = 0
    words_in_first_part = hook_text_parts[0].split()
    text_clips_ = []
    orig_hook_first_part_text = re.sub(r'\s+', ' ', orig_hook_text_parts[0])
    for word_data in word_color_data:
      for word_info in word_data:
        word = word_info['text'].capitalize(
        )  # Capitalize the first letter of the word

        # Only add the word to pango_text if it is in the first part
        if word_index < len(
            words_in_first_part
        ) and word == words_in_first_part[word_index].capitalize():
          color = word_info['color']

          # Override the color only if it's not black
          if color == (0, 0, 0):
            color = text_color  # Use the front-end color if the color is black

          color_hex = "#{:02x}{:02x}{:02x}".format(*color)

          # Apply the font directly in Pango markup
          word_index += 1
          char_index += len(word)
          pango_text += f'<span font_desc="Mu Font {fontsize1}" foreground="{color_hex}">{word}</span>'

          if char_index < len(
              orig_hook_first_part_text
          ) and orig_hook_first_part_text[char_index] == ' ':
            pango_text += ' '
            char_index += 1
    logging.info(f"Pango-formatted text: {pango_text}")

    # Create the text clip with Pango-formatted text for the first part
    try:
      text_clip1 = TextClip(
        pango_text.strip(),  # Pango-formatted string with word colors
        size=(max_width, None),
        method='pango',  # Enable Pango markup
        fontsize=fontsize1,
        color='white',  # Default color, overridden by Pango markup
        align='center'
      )
      logging.info(f"Debug: Created TextClip with size: {text_clip1.size}")
    except Exception as e:
      logging.error(f"Error creating TextClip: {e}")
      raise

    # Get the dimensions of the first text clip
    text_clip1_w, text_clip1_h = text_clip1.size
    if text_clip1_h > (min_red_area_h - 10):
      min_red_area_h = text_clip1_h + 10

    # Create background clip for the first part
    bg_clip1 = ColorClip(
      size=(OUT_VIDEO_WIDTH, min_red_area_h), color=top_box_color
    )

    text_clip1_y_offset = (min_red_area_h-text_clip1_h) / 2

    if is_tiktok == 1:
      padding_top = 380
      bg_clip1 = ColorClip(
        size=(OUT_VIDEO_WIDTH, int(min_red_area_h + ((padding_top//2)))),
        color=top_box_color
      )
      text_clip1_y_offset += (padding_top / 2)
      min_red_area_h += (padding_top / 2)
      padding_left = 0
      padding_right = 0
      # Yeni video boyutlarını padding ile hesaplayın
      adjusted_width = OUT_VIDEO_WIDTH - padding_left - padding_right
      adjusted_height = OUT_VIDEO_HEIGHT

      # Klipleri CompositeVideoClip içinde konumlandırın
      final_clip = CompositeVideoClip(
        [
          bg_clip1.set_position(
            (padding_left, 0)
          ),  # Arka plan klibi padding ile yerleştiriyoruz
          text_clip1.set_position(
            ("center", text_clip1_y_offset)
          ),  # TextClip için yukarıdan padding ekliyoruz
        ],
        size=(OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT)
      )
    else:
      final_clip = CompositeVideoClip(
        [
          bg_clip1.set_position((0, 0)),
          text_clip1.set_position(("center", text_clip1_y_offset)),
        ],
        size=(OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT)
      )

    # Process the second part (after the hyphen) if it exists
    if len(hook_text_parts) > 1:
      min_white_area_h = int(round(30 * y_multiplier))
      fontsize2 = int(round(15 * 0.6 * x_multiplier))

      if is_tiktok == 1:
        fontsize2 += 18 * 0.6
      elif OUT_VIDEO_WIDTH == 1920 and OUT_VIDEO_HEIGHT == 1080:
        fontsize2 -= 20 * 0.6
      else:
        fontsize2 += 6
      second_part_text = hook_text_parts[1]

      # Build Pango-formatted text string with color for the second part
      pango_text2 = ""
      word_index_second = 0
      words_in_second_part = second_part_text.split()
      for word_info in word_data:
        word = word_info['text'].capitalize()

        # Ensure word is part of the second part
        if word_index_second < len(
            words_in_second_part
        ) and word == words_in_second_part[word_index_second].capitalize():
          color = word_info['color']
          if color == (255, 255, 255):
            color = (0, 0, 0)  # Use default color if the color is black

          color_hex = "#{:02x}{:02x}{:02x}".format(*color)

          pango_text2 += f'<span font_desc="Mu Font {fontsize2}" foreground="{color_hex}">{word}</span> '
          word_index_second += 1
      # Create TextClip for the second part with Pango-formatted text
      text_clip2 = TextClip(
        pango_text2.strip(),
        size=(OUT_VIDEO_WIDTH - (x_margin*2), 0),
        method='pango',  # Enable Pango markup
        fontsize=fontsize2,
        color='black',  # Default color, overridden by Pango markup
        align='center',
      )
      text_clip2_w, text_clip2_h = text_clip2.size
      if text_clip2_h > min_white_area_h:
        min_white_area_h = text_clip2_h

      # Create background clip for the second part
      bg_clip2 = ColorClip(
        size=(OUT_VIDEO_WIDTH, min_white_area_h), color=(255, 255, 255)
      )

      text_clip2_y_offset = min_red_area_h + (min_white_area_h-text_clip2_h) / 2

      final_clip = CompositeVideoClip(
        [
          bg_clip1.set_position((0, 0)),
          bg_clip2.set_position((0, min_red_area_h)),
          text_clip1.set_position(('center', text_clip1_y_offset)),
          text_clip2.set_position((x_margin, text_clip2_y_offset)),
        ],
        size=(OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT)
      )

    # Clean up the temporary Fontconfig directory
    try:
      shutil.rmtree(temp_fontconfig_dir)
    except Exception as err:
      logging.error(f"Error removing Fontconfig directory: {err}")

    return final_clip

  except Exception as e:
    logging.error(f"Error in create_custom_text_clip: {e}")
    raise

def process_audio_on_videos(
  row,
  video_files,
  idx,
  input_df,
  hook_number,
  hook_text,
  num_videos_to_use,
  audio_clip,
  OUT_VIDEO_WIDTH,
  OUT_VIDEO_HEIGHT,
  output_videos_folder,
  total_rows,
  task_id,
  top_box_color,
  default_text_color,
  word_color_data,
  audio_file=None,
  add_watermark=False,
  is_tiktok=False
):
  # Remove underscores from the hook text for display
  cleaned_hook_text = hook_text.replace('_', '')

  row['Input Video Filename'] = [
    os.path.basename(considered_video) for considered_video in video_files
  ]
  input_df.at[idx, 'Input Video Filename'] = row['Input Video Filename']

  # Ensure num_videos_to_use is valid and non-zero
  if num_videos_to_use <= 0:
    logging.error(
      f"num_videos_to_use is 0 or less for hook {hook_number}, setting it to 1 to avoid division by zero."
    )
    num_videos_to_use = 1

  each_video_duration = audio_clip.duration / num_videos_to_use
  video_clips = []
  logging.debug(
    f"Audio clip duration: {audio_clip.duration}, num_videos_to_use: {num_videos_to_use}"
  )

  for considered_vid in video_files:
    try:
      # Ensure the video file exists
      if not os.path.exists(considered_vid):
        logging.error(f"Video file {considered_vid} does not exist.")
        continue

      # Log and process the video
      logging.info(f'Processing video: {considered_vid}')
      video_clip = VideoFileClip(considered_vid).subclip(0, each_video_duration)

      # Check if the video clip has valid duration
      if video_clip.duration <= 0:
        logging.error(
          f"Video {considered_vid} has invalid duration {video_clip.duration}. Skipping."
        )
        continue

      # Apply cropping to maintain aspect ratio without distortion
      video_clip = crop_to_aspect_ratio(
        video_clip, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT
      )

      # Add the clip to the list of video clips
      video_clips.append(video_clip)
    except Exception as e:
      logging.error(f"Error processing video {considered_vid}: {e}")
      continue

  # Ensure there are valid clips to concatenate
  if not video_clips:
    logging.error("No valid video clips were found for concatenation.")
    return None

  logging.info('Concatenating videos')
  final_video_clip = concatenate_videoclips(video_clips)
  logging.info('Concatenated videos')

  # Automatically adjust the font size based on video dimensions and text length
  auto_font_size = max(
    int(OUT_VIDEO_WIDTH / len(cleaned_hook_text) * 1.5), 20
  )  # Simple logic to adjust font size

  # Ensure correct word color data is used
  if idx < len(word_color_data):
    specific_word_color_data = word_color_data[idx]
  else:
    specific_word_color_data = [
    ]  # Fallback to an empty list if out of range (for safety)

  logging.info(f"Specific word color data: {specific_word_color_data}")
  # Pass specific_word_color_data to the custom text clip creation
  logging.info('Using the create_custom_text_clip method')
  custom_text_clip = create_custom_text_clip(
    cleaned_hook_text, OUT_VIDEO_WIDTH, OUT_VIDEO_HEIGHT, top_box_color,
    default_text_color, auto_font_size, specific_word_color_data, is_tiktok
  )
  logging.info('Used the create_custom_text_clip method')

  logging.info('Adding watermark to final video')

  final_clip = None
  if add_watermark:
    watermark = ImageClip("hooks/tools/watermark.png")
    width = custom_text_clip.size[0] + 650
    height = width * (watermark.size[1] / watermark.size[0])
    watermark = watermark.resize(height=height, width=width)
    watermark = watermark.set_position("center").set_duration(
      final_video_clip.duration
    )

    logging.info('Creating a CompositeVideoClip instance')
    final_clip = CompositeVideoClip(
      [
        final_video_clip.audio_fadein(0.2).audio_fadeout(0.2),
        final_video_clip,
        custom_text_clip,
        watermark,
      ]
    ).set_audio(audio_clip).set_duration(audio_clip.duration)
    logging.info("Created a CompositeVideoClip instance")
  else:
    logging.info('Creating a CompositeVideoClip instance')
    final_clip = CompositeVideoClip(
      [
        final_video_clip.audio_fadein(0.2).audio_fadeout(0.2),
        final_video_clip,
        custom_text_clip,
      ]
    ).set_audio(audio_clip).set_duration(audio_clip.duration)
    logging.info("Created a CompositeVideoClip instance")

  output_video_filename = os.path.join(output_videos_folder, f'hook_{idx}.mp4')
  logging.info(f"{output_videos_folder},'---------->output_videos_folder")

  final_clip.write_videofile(
    output_video_filename,
    temp_audiofile=os.path.join(output_videos_folder, f"temp-audio_{idx}.m4a"),
    remove_temp=False,
    codec='libx264',
    audio_codec="aac"
  )

  logging.info(f"Video processing completed successfully")
