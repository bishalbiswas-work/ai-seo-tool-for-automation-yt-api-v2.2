import os
import json
import requests
from bs4 import BeautifulSoup
import librosa
import soundfile as sf
from moviepy.editor import concatenate_videoclips, ImageClip, AudioFileClip, concatenate_audioclips
import io
from PIL import Image as PILImage
import openai
from elevenlabs import generate, play, voices, set_api_key
import tempfile
import numpy as np

import googletrans
from googletrans import Translator

translator = Translator()

available_voices = voices()


def load_api_keys(filename):
    keys = {}
    with open(filename, 'r') as file:
        for line in file:
            if '=' in line:
                name, key = line.strip().split('=')
                keys[name] = key
    return keys

keys = load_api_keys('api_keys.txt')

set_api_key(keys['elevenlabs'])   # elevenlabs
openai.api_key = keys['openai']   # openai








# Function to scrape content from a webpage
def scrape_page(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        page_content = soup.get_text(separator=' ', strip=True)
        word_count = len(page_content.split())
        return page_content, word_count
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"


# Function to generate a video script
def generate_video_script(topic, video_length):
    schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the video"
            },
            "description": {
                "type": "string",
                "description": "Brief description about the video content"
            },
            "script": {
                "type": "object",
                "description": "Full video script",
                "properties": {
                    "parts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "visuals": {"type": "string", "description": "Brief description about the scene"}
                            }
                        }
                    }
                }
            }
        }
    }

    prompt = f"Write a video title, description, and script for the topic '{topic}' that should be under '{video_length}' in length."
    messages = [
        {"role": "system", "content": "You are a helpful scriptwriter assistant."},
        {"role": "user", "content": prompt}
    ]
    
    error_message = None
    tries = 0

    while tries < 3:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            functions=[{"name": "set_video_details", "parameters": schema}],
            function_call={"name": "set_video_details"}
        )
        script = json.loads(response.choices[0].message.function_call["arguments"])
        
        # Check the structure and data of the script
        if ('title' in script and 'description' in script and 'script' in script and 
            'parts' in script['script'] and script['script']['parts']):
            break
        else:
            tries += 1

    if tries == 3:
        error_message = "Failed to generate a valid script after 3 attempts."

    # Ensure script content length is within the specified video length if script was received correctly
    if not error_message:
        total_content_length = sum(len(part['content'].split()) for part in script['script']['parts'])

        while total_content_length > video_length:
            last_part = script['script']['parts'].pop()
            total_content_length -= len(last_part['content'].split())

    return script, error_message


# Function to get audio
def get_audio(text, voice_type):
    voice_used  = None
    if voice_type == "male":
        voice_used = available_voices[3]
    else:
        voice_used = available_voices[0]

    audio = generate(text=text, voice=voice_used, model="eleven_monolingual_v1")
    return audio


# Function to generate a summary
def generate_summary(description, word_limit):
    prompt = f"Generate a summary for the given '{description}'. Limit the summary to {word_limit} words."
    messages = [
        {"role": "system", "content": "You are a helpful scriptwriter assistant."},
        {"role": "user", "content": prompt}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages
    )
    return response.choices[0].message.content


# Function to generate an image prompt
def generate_image_prompt(description, word_limit):
    prompt = f"Generate keywords for the given '{description}'. Limit keywords to under {word_limit} words."
    messages = [
        {"role": "system", "content": "You are a helpful scriptwriter assistant."},
        {"role": "user", "content": prompt}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages
    )
    return response.choices[0].message.content

def generate_better_prompts(description):
    # Instruction to GPT-3.5
    instruction = ("Transform the description '{description}' into a prompt suitable for DALL·E by "
                   "retaining only words that express physical attributes, removing any reference to text, "
                   "ensuring a single subject, and emphasizing a clear image with beautiful lighting centered on the subject.")

    prompt = instruction.format(description=description)

    messages = [
        {"role": "system", "content": "You are a helpful prompt writer assistant."},
        {"role": "user", "content": prompt}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=messages,
    )
    return response.choices[0].message.content


# Function to generate an image
def generate_image(prompt, image_count):

    response = openai.Image.create(
        prompt=prompt,
        n=image_count,
        size="1024x1024"
    )
    return [entry['url'] for entry in response['data']]


# Function to generate a social media post
def generate_social_media_post(topic, length):
    schema = {
        "type": "object",
        "properties": {
            "headline": {
                "type": "string",
                "description": "Headline or caption for the post"
            },
            "text": {
                "type": "string",
                "description": "Main content or body of the post"
            },
            "imageDescription": {
                "type": "string",
                "description": "Description of the accompanying image"
            },
            "hashtags": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of hashtags associated with the post, put # on each word"
            },
            "emojis": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of emojis used in the post"
            }
        }
    }

    prompt = f"Write a viral social media headline, text, imageDescription, hashtags, and emojis for the topic '{topic}' that is approximately '{length}' words in length."
    messages = [
        {"role": "system", "content": "You are a helpful social media poster maker assistant."},
        {"role": "user", "content": prompt}
    ]

    error_message = None
    tries = 0

    while tries < 3:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            messages=messages,
            functions=[{"name": "set_social_media_post_details", "parameters": schema}],
            function_call={"name": "set_social_media_post_details"}
        )
        post = json.loads(response.choices[0].message.function_call["arguments"])
        
        # Check the structure and data of the post
        if ('headline' in post and 'text' in post and 'imageDescription' in post and 
            'hashtags' in post and 'emojis' in post):
            break
        else:
            tries += 1

    if tries == 3:
        error_message = "Failed to generate a valid social media post after 3 attempts."

    return post, error_message



# Function to get audio duration from raw data
def get_audio_duration_from_raw(raw_audio):
    y, sr = librosa.load(io.BytesIO(raw_audio), sr=None)
    return librosa.get_duration(y=y, sr=sr)


# Function to save raw audio to a temporary file
def save_raw_audio_to_temp(raw_audio):
    temp_audio_file = tempfile.mktemp(suffix=".wav")
    y, sr = librosa.load(io.BytesIO(raw_audio), sr=None)
    sf.write(temp_audio_file, y, sr)
    return temp_audio_file


# Function to download images from URLs to memory
def download_images_from_urls_to_memory(image_urls):
    raw_images = []
    for url in image_urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            raw_images.append(response.content)
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
    return raw_images

def get_trans(content, language_code):
    translator = Translator()
    attempts = 3
    
    for _ in range(attempts):
        try:
            result = translator.translate(content, src='en', dest=language_code)
            return result.text
        except Exception as e:
            print(f"Error while translating, attempt {_ + 1}: {e}")

    print("Failed all translation attempts.")
    return None

# Function to generate a video
# def generate_video(raw_audios, image_url_groups, output_path):
#     video_clips = []
#     audio_clips = []
#     for idx, raw_audio in enumerate(raw_audios):
#         audio_duration = get_audio_duration_from_raw(raw_audio)
#         audio_path = save_raw_audio_to_temp(raw_audio)
#         audio = AudioFileClip(audio_path)
#         raw_images = download_images_from_urls_to_memory(image_url_groups[idx])
#         interval = audio_duration / len(raw_images)
#         clips = [ImageClip(np.array(PILImage.open(io.BytesIO(img_data)))).set_duration(interval) for img_data in raw_images]
#         video_segment = concatenate_videoclips(clips).set_audio(audio)
#         video_clips.append(video_segment)
#         audio_clips.append(audio)
#         os.remove(audio_path)
#     final_video = concatenate_videoclips(video_clips).set_audio(concatenate_audioclips(audio_clips))
#     final_video.write_videofile(output_path, codec='libx264', fps=24)

def generate_video(raw_audios, image_url_groups, output_path, video_width, video_height):
    video_clips = []
    audio_clips = []
    
    for idx, raw_audio in enumerate(raw_audios):
        audio_duration = get_audio_duration_from_raw(raw_audio)
        audio_path = save_raw_audio_to_temp(raw_audio)
        audio = AudioFileClip(audio_path)
        
        raw_images = download_images_from_urls_to_memory(image_url_groups[idx])
        interval = audio_duration / len(raw_images)
        
        # Modify the image size to match the desired video dimensions
        resized_images = [PILImage.open(io.BytesIO(img_data)).resize((video_width, video_height)) for img_data in raw_images]
        
        clips = [ImageClip(np.array(img)).set_duration(interval) for img in resized_images]
        video_segment = concatenate_videoclips(clips).set_audio(audio)
        
        video_clips.append(video_segment)
        audio_clips.append(audio)
        os.remove(audio_path)
    
    final_video = concatenate_videoclips(video_clips).set_audio(concatenate_audioclips(audio_clips))
    final_video.write_videofile(output_path, codec='libx264', fps=24)



def generate_url_video_and_social_mendia_post(url, video_width, video_height, video_length=130, voice_style="", language_code="", video_path="") :

    # Scrape content from a webpage
    # url = "https://www.betimeful.com/blogs/news-feed-eradicator"
    # video_length = 100 # 30 seconds
    post_words_limit = "130"
    content, word_count = scrape_page(url)
    print(content)
    prompt = generate_summary(content, "500")
    print(prompt)

    # Generate video script and social media post
    script_output, error_message = generate_video_script(prompt, int(video_length))
    if error_message == None:
        print(script_output)
        post_json, post_error_message = generate_social_media_post(prompt, post_words_limit)
        
        if post_error_message == None:
            print(post_json)

            # Generate audios and images for the video script
            audios = []
            image_url_groups = []
            for part in script_output['script']['parts']:
                if language_code != "en":
                    result = get_trans(part['content'], language_code)
                else:
                    result = part['content']
                audio = get_audio(result, voice_style)
                audios.append(audio)
                # play_audio = Audio(audio)
                # display(play_audio)
                # image_prompt = generate_image_prompt(part['visuals'], "30 words")
                image_prompt = generate_better_prompts(part['visuals'])   # Better Image prompts for dalle
                image_urls_for_part = generate_image(image_prompt, 4)
                image_url_groups.append(image_urls_for_part)
            generate_video(audios, image_url_groups, video_path, video_width, video_height)
            return post_json
        else:
            print(post_error_message)
    else:
        print(error_message)

def generate_prompt_video_and_social_mendia_post(prompt, video_width, video_height, video_length=130, voice_style="", language_code="", video_path="") :

    error_message = None
    post_words_limit = "130"
    # Generate video script and social media post
    script_output, error_message = generate_video_script(prompt, int(video_length))
    if error_message == None:
        print(script_output)
        post_json, post_error_message = generate_social_media_post(prompt, post_words_limit)
        
        if post_error_message == None:
            print(post_json)

            # Generate audios and images for the video script
            audios = []
            image_url_groups = []
            for part in script_output['script']['parts']:
                if language_code != "en":
                    result = get_trans(part['content'], language_code)
                else:
                    result = part['content']

                audio = get_audio(result, voice_style)
                audios.append(audio)
                # play_audio = Audio(audio)
                # display(play_audio)
                # image_prompt = generate_image_prompt(part['visuals'], "30 words")
                image_prompt = generate_better_prompts(part['visuals'])   # Better Image prompts for dalle
                image_urls_for_part = generate_image(image_prompt, 4)
                image_url_groups.append(image_urls_for_part)
            generate_video(audios, image_url_groups, video_path, video_width, video_height)
            return post_json
        else:
            print(post_error_message)
    else:
        print(error_message)

def generate_prompt_to_thumbnail(prompt):
    image_prompt = generate_better_prompts(prompt)   # Better Image prompts for dalle
    image_urls_for_part = generate_image(image_prompt, 1)
    print(image_urls_for_part)
    return image_urls_for_part[0]

def generate_url_to_thumbnail(url):
    content, word_count = scrape_page(url)
    print(content)
    prompt = generate_summary(content, "50")
    image_prompt = generate_better_prompts(prompt)   # Better Image prompts for dalle
    image_urls_for_part = generate_image(image_prompt, 1)
    return image_urls_for_part[0]