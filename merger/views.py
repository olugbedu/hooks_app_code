# merger/views.py
import boto3
import os
import subprocess
import zipfile
import re
import io
import shutil
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, FileResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from urllib.parse import unquote  # Corrected import
import requests
from urllib.parse import urlparse
from .forms import VideoUploadForm
from .models import MergeTask
import uuid
from datetime import datetime



# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)



# Creating a connection to the aws s3 bucket 
# aws_access_key_id: aws secret key 
# aws_secret_access_key: aws s3 secret key
# region_name: aws region obtained from aws bucket name
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)


def generate_task_id():
    """
    Generate a unique identifier for each task.
    Returns:
        uuid4: return a unique identifier everytime
    """
    return str(uuid.uuid4())



def sanitize_filename(filename):
    """
    Removes or replaces characters that are unsafe for filenames.
    """
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Remove any character that is not alphanumeric, underscore, hyphen, or dot
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    return filename



def has_audio(video_file):
    """
    Check if the video file has an audio stream.
    """
    command = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        video_file
    ]
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        output = result.stdout.strip()
        return output == "audio"
    except subprocess.CalledProcessError as e:
        logging.error(f"FFprobe error when checking audio for {video_file}: {e.stderr.strip()}")
        return False
    
    

def ffprobe_get_frame_count(video_filepath):
    """
    Uses ffprobe to count the number of video frames in a video file.
    """
    command = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-count_frames',
        '-show_entries', 'stream=nb_read_frames',
        '-of', 'csv=p=0',
        video_filepath,
    ]
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        output = result.stdout.strip()
        if output.isdigit():
            return int(output)
        else:
            logging.error(f"Couldn't get frame count for {video_filepath}: {result.stderr.strip()}")
            return 0
    except subprocess.CalledProcessError as e:
        logging.error(f"FFprobe error for {video_filepath}: {e.stderr.strip()}")
        return 0
    
    

def check_video_format_resolution(video_file):
    """
    Uses ffprobe to retrieve the width and height of the first video stream.
    Ensures that both width and height are even numbers.
    """
    command = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        video_file
    ]
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        output = result.stdout.strip().split('\n')
        resolutions = [line.strip() for line in output if 'x' in line and line.strip()]
        if resolutions:
            try:
                width_str, height_str = resolutions[0].split('x')[:2]
                width = int(width_str.strip())
                height = int(height_str.strip())
                # Ensure dimensions are even
                width = width if width % 2 == 0 else width + 1
                height = height if height % 2 == 0 else height + 1
                return width, height
            except ValueError as e:
                logging.error(f"Error parsing resolution: {resolutions[0]} - {e}")
                return None, None
        else:
            logging.error(f"Could not determine resolution for video: {video_file}")
            return None, None
    except subprocess.CalledProcessError as e:
        logging.error(f"FFprobe error for {video_file}: {e.stderr.strip()}")
        return None, None
    
    

def preprocess_video(input_file, output_file, reference_resolution=None, merge_task=None):
    """
    Preprocesses a video by scaling it to the reference resolution and ensuring consistent encoding.
    Ensures that the output dimensions are even and that audio streams are present.
    If the input video lacks an audio stream, adds a silent audio track.
    """
    logging.info(f"Preprocessing video: {input_file}")

    # Check if the input video has an audio stream
    input_has_audio = has_audio(input_file)

    if input_has_audio:
        # Video with audio: scale and encode
        command = ["ffmpeg", "-y", "-i", input_file]

        if reference_resolution:
            width, height = reference_resolution
            # Scale with aspect ratio preservation and enforce even dimensions
            vf_filter = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                f"format=yuv420p"
            )
            command += ["-vf", vf_filter]

        # Ensure audio is encoded
        command += [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-r", "30",  # Enforce frame rate
            output_file
        ]
    else:
        # Video without audio: add silent audio
        command = [
            "ffmpeg", "-y", "-i", input_file,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        ]

        if reference_resolution:
            width, height = reference_resolution
            vf_filter = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                f"format=yuv420p"
            )
            command += ["-vf", vf_filter]

        # Map video and silent audio
        command += [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-shortest",
            "-pix_fmt", "yuv420p",
            "-r", "30",  # Enforce frame rate
            output_file
        ]

    logging.debug(f"Preprocess command: {' '.join(command)}")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )

    frames_processed = 0
    prev_frames_processed = 0
    while True:
        output = process.stderr.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            logging.debug(output.strip())
            match = re.search(r"frame=\s*(\d+)", output)
            if match:
                frames_processed = int(match.group(1))
                if frames_processed - prev_frames_processed >= 150:
                    if merge_task:
                        merge_task.total_frames_done += (frames_processed - prev_frames_processed)
                        merge_task.save()
                    prev_frames_processed = frames_processed

    return_code = process.wait()
    if return_code != 0:
        logging.error(f"FFmpeg failed during preprocessing of {input_file}. Check logs above for details.")
        # Remove the invalid output file if FFmpeg failed
        if os.path.exists(output_file):
            os.remove(output_file)
            logging.info(f"Removed invalid preprocessed file: {output_file}")
        return

    if merge_task:
        merge_task.total_frames_done += (frames_processed - prev_frames_processed)
        merge_task.save()

    logging.info(f"Finished preprocessing: {output_file}")
    
    
    

def concatenate_videos(input_files, output_file, merge_task):
    """
    Concatenates multiple video files into a single output file using FFmpeg's concat filter.
    """
    logging.info(f"Concatenating videos into: {output_file}")
    if len(input_files) < 2:
        logging.error("Need at least two files to concatenate")
        return

    # Build FFmpeg command with filter_complex 'concat'
    command = ['ffmpeg', '-y']
    for input_file in input_files:
        command += ['-i', input_file]

    # Construct the filter_complex string
    filter_complex = ""
    for i in range(len(input_files)):
        filter_complex += f"[{i}:v][{i}:a]"
    filter_complex += f"concat=n={len(input_files)}:v=1:a=1[outv][outa]"

    command += [
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'libx264',
        '-preset', 'superfast',
        '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        '-r', '30',
        output_file
    ]

    logging.debug(f"Concatenate command: {' '.join(command)}")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )

    frames_processed = 0
    prev_frames_processed = 0
    ffmpeg_error = ""
    while True:
        output = process.stderr.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            logging.debug(output.strip())
            ffmpeg_error += output
            match = re.search(r"frame=\s*(\d+)", output)
            if match:
                frames_processed = int(match.group(1))
                if frames_processed - prev_frames_processed >= 150:
                    if merge_task:
                        merge_task.total_frames_done += (frames_processed - prev_frames_processed)
                        merge_task.save()
                    prev_frames_processed = frames_processed

    return_code = process.wait()
    if return_code != 0:
        logging.error(f"FFmpeg failed during concatenation of {output_file}.")
        logging.error(f"FFmpeg error output: {ffmpeg_error}")
        # Remove the invalid output file if FFmpeg failed
        if os.path.exists(output_file):
            os.remove(output_file)
            logging.info(f"Removed invalid concatenated file: {output_file}")
        return

    if merge_task:
        merge_task.total_frames_done += (frames_processed - prev_frames_processed)
        merge_task.save()

    logging.info(f"Finished concatenating: {output_file}")
    
    
    
    
    
def generate_presigned_url(bucket_name, object_key, expiration=3600):
    """
    Generate a presigned URL to download the S3 object.
    object_key: aws media link 
    expiration: expiration time in seconds (default: 3600 seconds)
    """
    try:
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return response
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None
    
    

def download_video_from_s3(s3_url, local_folder):
    """
    Download an S3 file to a local folder using a presigned URL.
    s3_url: The presigned URL to download the file from S3
    local_folder: The local folder to save the downloaded file
    """
    # Parse the S3 URL
    parsed_url = urlparse(s3_url)
    bucket_name = parsed_url.netloc.split('.')[0]  # Extract the bucket name
    bucket_name = bucket_name if bucket_name else settings.AWS_STORAGE_BUCKET_NAME
    object_key = parsed_url.path.lstrip('/')       # Extract the object key

    # Generate a presigned URL
    presigned_url = generate_presigned_url(bucket_name, object_key)
    if not presigned_url:
        print("Failed to generate a presigned URL")
        return

    # Fetch the file and save it locally
    local_file_path = os.path.join(local_folder, os.path.basename(object_key))
    try:
        response = requests.get(presigned_url, stream=True)
        if response.status_code == 200:
            with open(local_file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
            print(f"File downloaded successfully: {local_file_path}")
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading the file: {e}")

    
    
def upload_to_s3(file_path, bucket_name, s3_key):
    """
    Uploads a file to an S3 bucket.
    file_path: The path to the local file to be uploaded
    bucket_name: The S3 bucket where the file will be uploaded
    s3_key: The key under which the file will be stored in S3
    """
    try:
        s3_client.upload_file(file_path, bucket_name, s3_key)
        file_url = f"https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
        logging.info(f"Uploaded preprocessed video to S3: {file_url}")
        return file_url
    except Exception as e:
        logging.error(f"Error uploading to S3: {e}")
        raise
    
    

def process_videos(task_id):
    """
    Orchestrates the preprocessing and concatenation of videos for a given task.
    
    """
    logging.info("Starting video processing...")

    try:
        merge_task = MergeTask.objects.get(task_id=task_id)
    except MergeTask.DoesNotExist:
        logging.error(f"MergeTask with task_id {task_id} does not exist.")
        return

    short_videos = merge_task.short_video_path
    large_videos = merge_task.large_video_paths

    if not large_videos:
        logging.error("No large videos found for merging.")
        merge_task.status = 'failed'
        merge_task.save()
        return

    # Determine reference resolution from the first large video
    ref_resolution = check_video_format_resolution(large_videos[0])
    if not ref_resolution or not ref_resolution[0] or not ref_resolution[1]:
        logging.error("Invalid reference resolution. Cannot preprocess videos.")
        merge_task.status = 'failed'
        merge_task.save()
        return

    reference_resolution = ref_resolution
    logging.info(f"Reference resolution: {reference_resolution}")

    # Preprocess short videos
    preprocessed_short_files = []
    short_video_names = []
    with ThreadPoolExecutor() as executor:
        futures = []
        for video in short_videos:
            short_name = os.path.splitext(os.path.basename(video))[0]
            short_video_names.append(short_name)
            preprocessed_filename = f"preprocessed_{os.path.basename(video)}"
            output_file = os.path.join(settings.OUTPUT_FOLDER, preprocessed_filename)
            download_video_from_s3(video, output_file) # function to download video to the temporary local folder for processing
            futures.append(executor.submit(preprocess_video, video, output_file, reference_resolution, merge_task))
            preprocessed_short_files.append(output_file)

        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error during preprocessing: {e}")
                merge_task.status = 'failed'
                merge_task.save()
                return

    # Preprocess large videos
    preprocessed_large_files = []
    large_video_names = []
    with ThreadPoolExecutor() as executor:
        futures = []
        for video in large_videos:
            large_name = os.path.splitext(os.path.basename(video))[0]
            large_video_names.append(large_name)
            preprocessed_filename = f"preprocessed_{os.path.basename(video)}"
            output_file = os.path.join(settings.OUTPUT_FOLDER, preprocessed_filename)
            download_video_from_s3(video, output_file)
            futures.append(executor.submit(preprocess_video, video, output_file, reference_resolution, merge_task))
            preprocessed_large_files.append(output_file)

        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error during preprocessing: {e}")
                merge_task.status = 'failed'
                merge_task.save()
                return

    # Validate that preprocessed videos have video and audio streams
    valid_preprocessed_short_files = []
    valid_short_names = []
    for pre_file, sname in zip(preprocessed_short_files, short_video_names):
        w, h = check_video_format_resolution(pre_file)
        if w and h:
            valid_preprocessed_short_files.append(pre_file)
            valid_short_names.append(sname)
        else:
            logging.error(f"Preprocessed file {pre_file} does not contain a valid video stream.")

    if not valid_preprocessed_short_files:
        logging.error("No valid preprocessed short videos available for concatenation.")
        merge_task.status = 'failed'
        merge_task.save()
        return

    valid_preprocessed_large_files = []
    valid_large_names = []
    for pre_file, lname in zip(preprocessed_large_files, large_video_names):
        w, h = check_video_format_resolution(pre_file)
        if w and h:
            valid_preprocessed_large_files.append(pre_file)
            valid_large_names.append(lname)
        else:
            logging.error(f"Preprocessed file {pre_file} does not contain a valid video stream.")

    if not valid_preprocessed_large_files:
        logging.error("No valid preprocessed large videos available for concatenation.")
        merge_task.status = 'failed'
        merge_task.save()
        return

    # Now, concatenate each preprocessed short video with each preprocessed large video
    final_output_files = []
    with ThreadPoolExecutor() as executor:
        concat_futures = []
        for large_video, large_name in zip(valid_preprocessed_large_files, valid_large_names):
            # Concatenate each short video with the large video
            for short_file, sname in zip(valid_preprocessed_short_files, valid_short_names):
                # Remove 'preprocessed_' prefix for naming
                short_base = os.path.splitext(os.path.basename(short_file))[0].replace('preprocessed_', '')
                large_base = os.path.splitext(os.path.basename(large_video))[0].replace('preprocessed_', '')
                final_output_name = f"{short_base}_{large_base}.mp4"
                final_output = os.path.join(settings.OUTPUT_FOLDER, final_output_name)
                concat_futures.append(
                    executor.submit(concatenate_videos, [short_file, large_video], final_output, merge_task)
                )

                # Store relative paths
                relative_output = os.path.relpath(final_output, settings.MEDIA_ROOT)
                final_output_files.append({
                    'video_link': relative_output.replace('\\', '/'),  # Ensure URL-friendly paths
                    'file_name': final_output_name
                })

        for future in concat_futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error during concatenation: {e}")
                merge_task.status = 'failed'
                merge_task.save()
                return
    updated_video_links = []
    for video in final_output_files:
            video_file_path = video.get('video_link')
            video_file_name = video.get('file_name')
            if video_file_path:
                s3_key = f"output_merger_videos/task_{task_id}/{video_file_name}"
                video_url = upload_to_s3(video_file_path, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
                updated_video_links.append({
                    "file_name": video_file_name,
                    "video_link": video_url
                })

    logging.info("Video processing complete!")
    merge_task.status = 'completed'
    merge_task.video_links = updated_video_links
    merge_task.save()
    
    try:
        # Delete temporary files
        if os.path.exists(settings.OUTPUT_FOLDER):
            shutil.rmtree(settings.OUTPUT_FOLDER)
            print(f"Directory '{settings.OUTPUT_FOLDER}' removed successfully.")
        else:
            print(f"Directory '{settings.OUTPUT_FOLDER}' does not exist.")
    except Exception as e:
        print(f"Error removing directory '{settings.OUTPUT_FOLDER}': {e}")
        
        
        
        


@login_required
def index(request):
    """
    Renders the video upload form.
    """
    form = VideoUploadForm()
    return render(request, 'merger/index.html', {'form': form})




def upload_to_s3(file_path, bucket_name, s3_key):
    """
    Upload a file to an S3 bucket and return the URL.
    Args:
        file_path: Path to the file on the local filesystem.
        bucket_name: Name of the S3 bucket.
        s3_key: Path in the S3 bucket where the file will be stored.

    Returns:
        str: URL of the uploaded file.
    """
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        s3_client.upload_file(
            Filename=file_path,
            Bucket=bucket_name,
            Key=s3_key
        )
        file_url = f"https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
        logging.info(f"File uploaded to S3: {file_url}")
        return file_url
    except Exception as e:
        logging.error(f"Error uploading to S3: {e}")
        raise



@require_POST
@login_required
def upload_files(request):
    """
    Handles the upload of short and large videos and saves them to S3.
    """
    # Validate file sizes
    max_upload_size = getattr(settings, 'FILE_UPLOAD_MAX_MEMORY_SIZE', 10485760)  # Default 10MB
    for file in request.FILES.getlist('large_videos'):
        if file.size > max_upload_size:
            messages.error(request, "One of the large videos exceeds the maximum allowed size.")
            return redirect(reverse('merger:index'))

    task_id = generate_task_id()
    logging.info(f'Merge Task ID generated --> {task_id}')

    MergeTask.objects.create(task_id=task_id, status='processing')
    logging.info(f'A Merge Task object created for merge task id --> {task_id}')

    short_videos = request.FILES.getlist('short_videos')
    large_videos = request.FILES.getlist('large_videos')

    logging.info(f'Short videos uploaded: {short_videos}')
    logging.info(f'Large videos uploaded: {large_videos}')

    short_video_urls = []
    large_video_urls = []

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME  # Replace with your S3 bucket name
    upload_dir = f"merger_upload_video/{task_id}"  # Directory in S3 for this task

    # Save and upload short videos to S3
    for file in short_videos:
        original_filename = sanitize_filename(file.name)
        local_file_path = f"/tmp/{original_filename}"
        with open(local_file_path, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)

        s3_key = f"{upload_dir}/short_videos/{original_filename}"
        try:
            url = upload_to_s3(local_file_path, bucket_name, s3_key)
            short_video_urls.append(url)
        except Exception as e:
            logging.error(f"Error uploading short video {original_filename}: {e}")
            messages.error(request, f"Error uploading short video {original_filename}.")
            return redirect(reverse('merger:index'))
        finally:
            os.remove(local_file_path)  # Clean up the temporary file

    # Save and upload large videos to S3
    for file in large_videos:
        original_filename = sanitize_filename(file.name)
        local_file_path = f"/tmp/{original_filename}"
        with open(local_file_path, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)

        s3_key = f"{upload_dir}/large_videos/{original_filename}"
        try:
            url = upload_to_s3(local_file_path, bucket_name, s3_key)
            large_video_urls.append(url)
        except Exception as e:
            logging.error(f"Error uploading large video {original_filename}: {e}")
            messages.error(request, f"Error uploading large video {original_filename}.")
            return redirect(reverse('merger:index'))
        finally:
            os.remove(local_file_path)  # Clean up the temporary file

    logging.info(f'Short video URLs: {short_video_urls}')
    logging.info(f'Large video URLs: {large_video_urls}')

    # Update MergeTask with uploaded URLs
    merge_task = MergeTask.objects.get(task_id=task_id)
    merge_task.short_video_path = short_video_urls
    merge_task.large_video_paths = large_video_urls
    merge_task.save()

    # Calculate total frames for progress tracking
    total_short_video_frames = sum(ffprobe_get_frame_count(url) for url in short_video_urls)
    total_long_video_frames = sum(ffprobe_get_frame_count(url) for url in large_video_urls)
    total_frames = total_short_video_frames + (len(large_videos) * total_short_video_frames) + (len(short_videos) * total_long_video_frames)
    merge_task.total_frames = total_frames if total_frames > 0 else 1
    merge_task.save()

    return JsonResponse({'taskId': task_id})




@login_required
def processing(request, task_id):
    """
    Initiates the video processing in a separate thread.
    """
    try:
        merge_task = MergeTask.objects.get(task_id=task_id)
    except MergeTask.DoesNotExist:
        return HttpResponse("Task not found.", status=404)

    merge_credits_used = len(merge_task.short_video_path)
    if request.user.subscription.merge_credits < merge_credits_used:
        return HttpResponse(
            "You don't have enough merge credits, buy and try again!", status=403
        )

    thread = threading.Thread(target=process_videos, args=(task_id,))
    thread.start()

    # Deduct merge credits
    request.user.subscription.merge_credits -= merge_credits_used
    request.user.subscription.save()
    logging.info(f"Used {merge_credits_used} merge credits")

    return render(request, 'merger/processing.html', {'task_id': task_id})




@login_required
def get_progress(request, task_id):
    """
    Returns the progress of the video processing task.
    """
    merge_task = get_object_or_404(MergeTask, task_id=task_id)
    if merge_task.total_frames == 0:
        progress = 0
    else:
        progress = int(min(1, (merge_task.total_frames_done / merge_task.total_frames)) * 100)

    return JsonResponse({'progress': progress})




@login_required
def check_task_status(request, task_id):
    """
    Returns the status of the video processing task along with video links if completed.
    """
    task = get_object_or_404(MergeTask, task_id=task_id)
    return JsonResponse({
        'status': task.status,
        'video_links': task.video_links if task.status == 'completed' else None
    })



@login_required
def processing_successful(request, task_id):
    """
    Renders a success page with links to the processed videos.
    """
    task = get_object_or_404(MergeTask, task_id=task_id)
    return render(
        request, 'merger/processing_successful.html', {
            'task_id': task_id,
            'video_links': task.video_links
        }
    )



@login_required
def download_video(request):
    """
    Downloads a video from S3 using a pre-signed URL.
    
    """
    videopath = request.GET.get('videopath', None)
    if not videopath:
        return HttpResponse("No video path provided", status=400)
    parsed_url = urlparse(videopath)
    bucket_name = parsed_url.netloc.split('.')[0]
    object_key = parsed_url.path.lstrip('/')
    presigned_url = generate_presigned_url(bucket_name, object_key)
    if not presigned_url:
        return HttpResponse("Unable to generate download link", status=500)
    try:
        response = requests.get(presigned_url, stream=True)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            response_stream = HttpResponse(response.iter_content(chunk_size=1024), content_type=content_type)
            response_stream['Content-Disposition'] = f'attachment; filename="{os.path.basename(object_key)}"'
            return response_stream
        else:
            return HttpResponse("Failed to download video from S3", status=response.status_code)
    except Exception as e:
        return HttpResponse(f"Error while downloading the file: {str(e)}", status=500)   




@login_required
def download_zip(request, task_id):
    """
    Creates and serves a ZIP archive of all processed videos for a given task.
    """
    task = get_object_or_404(MergeTask, task_id=task_id)
    videos = task.video_links or []

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for video in videos:
            # process the video for each video link
            video_link = video.get('video_link')
            if video_link:
                absolute_video_path = os.path.join(settings.MEDIA_ROOT, video_link)
                if os.path.exists(absolute_video_path):
                    file_name = os.path.basename(absolute_video_path)
                    try:
                        zip_file.write(absolute_video_path, file_name)
                    except Exception as e:
                        logging.error(f"Error adding {absolute_video_path} to zip: {e}")
                else:
                    logging.warning(f"Video file for zipping not found: {absolute_video_path}")

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="final_videos.zip"'
    return response