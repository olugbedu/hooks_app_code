import logging
import tempfile
import os
import shutil
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, FileResponse
from django.conf import settings
from urllib.parse import urlparse
from .forms import HookForm
from botocore.exceptions import NoCredentialsError
from .tools.utils import generate_task_id
from .tools.processor import process_files

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import SuspiciousOperation
from .models import Task
from account.models import Plan
import threading
import zipfile
import io
import boto3
import requests
from .tools.spreadsheet_extractor import fetch_google_sheet_data
from django.conf import settings

logging.basicConfig(level=logging.DEBUG)


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



def upload_to_s3(file_path, bucket_name, s3_key):
    """Upload a file to an S3 bucket and return the URL."""
    try:
        s3_client.upload_file(file_path, bucket_name, s3_key)
        file_url = f"https://{bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}" # bucket url to save the video file
        logging.info(f"Video uploaded to S3: {file_url}")
        return file_url
    except Exception as e:
        logging.error(f"Error uploading to S3: {e}")
        raise
      
      
      

def background_processing(task_id, user_sub, aspect_ratio):
    """Background processing for the given task."""
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"task_{task_id}_")
        logging.info(f"Temporary directory created: {temp_dir}")
        video_links, credits_used = process_files(
            temp_dir,
            task_id,
            user_sub.plan.name.lower() == 'free',
            aspect_ratio
        )
        logging.info(f"Video Links: {video_links}")
        logging.info(f"Credits Used: {credits_used}")
        user_sub.hooks -= credits_used
        user_sub.save()
        logging.info(f"User credits reduced by {credits_used}. New credit balance: {user_sub.hooks}")
        updated_video_links = []
        for video in video_links: # looping through all the video link and upload them to s3 server
            video_file_path = video.get('video_link') 
            video_file_name = video.get('file_name')
            if video_file_path:
                s3_key = f"output_videos/task_{task_id}/{video_file_name}"
                video_url = upload_to_s3(video_file_path, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
                updated_video_links.append({
                    "file_name": video_file_name,
                    "video_link": video_url
                })  # appending each return url into updated_video_links llst
        task = Task.objects.get(task_id=task_id)
        task.status = 'completed'
        task.video_links = updated_video_links
        task.aspect_ratio = aspect_ratio
        task.save()
        logging.info(f"Task {task_id} updated to 'completed' with video URLs.")


    except Exception as e:
        logging.error(f"Error during background processing: {e}")

    finally:
        try:
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir)
                logging.info(f"Temporary directory {temp_dir} deleted.")
        except Exception as cleanup_error:
            logging.error(f"Error during temporary directory cleanup: {cleanup_error}")
            
            
    


@login_required
def upload_hook(request):
  """View to handle uploading a hook video."""
  
  if not request.user.is_authenticated:
    return redirect('account:home')

  hook = None
  if request.method == 'POST':
    task_id = generate_task_id()
    logging.info(f'Task ID generated --> {task_id}')

    Task.objects.create(task_id=task_id, status='processing')
    logging.info(f'A Task object created for task id --> {task_id}')

    parallel_processing = True

    form = HookForm(request.POST, request.FILES)
    is_valid_resolution = request.POST.get('resolution') in [
      'option1', 'option2', 'option3', 'option4'
    ]
    is_valid_form = form.is_valid() and \
                    is_valid_resolution
    if is_valid_form:
      hook = form.save(commit=False)
      hook.task_id = task_id
      hook.parallel_processing = parallel_processing
      hook.dimension = request.POST.get('resolution')
      hook.save()

      return redirect(
        'hooks:processing', task_id=task_id, aspect_ratio=hook.dimension
      )
    else:
      return render(request, 'upload_hook.html', {'form': form, 'hook': hook})
  else:
    form = HookForm()

  return render(request, 'upload_hook.html', {'form': form, 'hook': hook})



@login_required
def processing(request, task_id, aspect_ratio):

  # Check if the user has enough credits
  user_sub = request.user.subscription
  if not user_sub or user_sub.hooks <= 0:
    # You can change the url below to the stripe URL
    # return redirect('hooks:no_credits')  # Redirect to an error page or appropriate view
    return HttpResponse(
      "You don't have enough credits, buy and try again!", status=404
    )

  thread = threading.Thread(
    target=background_processing, args=(task_id, user_sub, aspect_ratio)
  )
  thread.start()

  return render(
    request, 'processing.html', {
      'task_id': task_id,
      'aspect_ratio': aspect_ratio,
    }
  )



@login_required
def check_task_status(request, task_id):
  task = get_object_or_404(Task, task_id=task_id)

  # Return task status and video links (if processing is completed)
  return JsonResponse(
    {
      'status': task.status,
      'video_links': task.video_links if task.status == 'completed' else None
    }
  )
  
  
  

def processing_successful(request, task_id):
  """View to display processing successful page."""
  
  task = get_object_or_404(Task, task_id=task_id)

  return render(
    request, 'processing_successful.html', {
      'task_id': task_id,
      'video_links': task.video_links,
      'plans': Plan.objects.all(),
    }
  )
  


def generate_presigned_url(bucket_name, object_name, expiration=3600):
    try:
        # Generate a presigned URL to download the S3 object
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name, 'Key': object_name},
                                                    ExpiresIn=expiration)
    except NoCredentialsError:
        return None
    
    return response
  


def download_video(request):
    """
    View to download a video from the S3 bucket.

    # Get the video path from the request query parameters
    videopath = request.GET.get('videopath', None)
    if not videopath this get the video path from the the frontend as the query parameters
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




def download_zip(request, task_id):
  task = get_object_or_404(Task, task_id=task_id)
  videos = task.video_links

  zip_buffer = io.BytesIO()

  with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
    for idx, video in enumerate(videos):
      if os.path.exists(video['video_link']):
        file_name = os.path.basename(video['video_link'])

        # Add the file to the zip archive
        zip_file.write(video['video_link'], file_name)

  zip_buffer.seek(0)

  # Create a response with the zip file for downloading
  response = HttpResponse(zip_buffer, content_type='application/zip')
  response['Content-Disposition'] = f'attachment; filename="hook_videos.zip"'

  return response



@login_required
def validate_google_sheet_link(request):
  """
    View to validate Google Sheets link.
  """
  if request.method == 'POST':
    google_sheets_link = request.POST.get('google_sheets_link')

    try:
      # Attempt to fetch the Google Sheets data for validation
      fetch_google_sheet_data(google_sheets_link)
      return JsonResponse({'valid': True})
    except ValueError as ve:
      return JsonResponse({'valid': False, 'error': str(ve)})
    except Exception as e:
      return JsonResponse({'valid': False, 'error': str(e)})

  return JsonResponse({'valid': False, 'error': 'Invalid request method.'})




def validate_api_key(request):
    """
    View to validate Eleven Labs API key.
    """
    if request.method == 'POST':
        api_key = request.POST.get('eleven_labs_api_key', '')
        voice_id = request.POST.get('voice_id')

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": api_key}
        data = {
            "text": "Test voice synthesis",
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                return JsonResponse({'valid': True})
            else:
                error_detail = response.json().get('detail', {})
                return JsonResponse({'valid': False, 'error': error_detail.get('status'), 'message': error_detail.get('message')})
        except requests.exceptions.RequestException:
            return JsonResponse({'valid': False, 'error': 'Error Connecting To Eleven Labs API', 'message': 'Error Connecting To Eleven Labs API'})
