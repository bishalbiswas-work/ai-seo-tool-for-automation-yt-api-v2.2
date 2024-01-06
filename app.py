from content_generation import *
import asyncio
from fastapi import BackgroundTasks
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

hostname = "api.clipify.club"
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [
    "http://localhost:3000",
      "http://localhost:8000",
    "http://clipify.club",
    "https://clipify.club",
    "http://www.clipify.club",
    "https://www.clipify.club",
    
    "http://autoyoutube.pro",
    "https://autoyoutube.pro",
    "http://www.autoyoutube.pro",
    "https://www.autoyoutube.pro",
    
    "http://messengergpt.pro",
    "https://messengergpt.pro",
    "http://www.messengergpt.pro",
    "https://www.messengergpt.pro",
    
    "http://translify.club",
    "https://translify.club",
    "http://www.translify.club",
    "https://www.translify.club"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(security)):
    correct_token = "sdfgdsfgU6wdtse1tYYMGRBAj2PyQTqJZm5OWGRJNbFi1y4dfmUu9iSnmp5fCHlsSeNv"
    if authorization.credentials != correct_token:
        raise HTTPException(status_code=401, detail="Incorrect token or token expired")
    return authorization.credentials

class url_VideoInput(BaseModel):
    url: str
    video_length: int
    voice_type: str
    language_code: str
    video_width: int
    video_height: int

class prompt_VideoInput(BaseModel):
    prompt: str
    video_length: int
    voice_type: str
    language_code: str
    video_width: int
    video_height: int

class prompt_thumbnail_input(BaseModel):
    prompt: str

class url_thumbnail_input(BaseModel):
    url: str

class url_thumbnail_output(BaseModel):
    url: str

class VideoOutput(BaseModel):
    video_path: str
    social_media_post: dict

# def generate_output(url: str, video_length: int, voice_type: str) -> str:    
#     return video_path

async def delete_video_after_delay(video_path: str, delay_seconds: int = 3600):
    await asyncio.sleep(delay_seconds)
    if os.path.exists(video_path):
        os.remove(video_path)
        print(f"Deleted video at {video_path}")



@app.post("/generate_url_to_thumbnail", response_model=url_thumbnail_output)
def generate_url_to_thumbnail_endpoint(video_data: url_thumbnail_input, token: str = Depends(get_current_user)):
    url = generate_url_to_thumbnail(video_data.url)

    return {"url":url}

@app.post("/generate_prompt_to_thumbnail", response_model=url_thumbnail_output)
def generate_prompt_to_thumbnail_endpoint(video_data: prompt_thumbnail_input, token: str = Depends(get_current_user)):
    url = generate_prompt_to_thumbnail(video_data.prompt)

    return {"url":url}

@app.post("/generate_url_video_and_social_media_post", response_model=VideoOutput)
def generate_video_and_social_mendia_post_endpoint(video_data: url_VideoInput,  background_tasks: BackgroundTasks, token: str = Depends(get_current_user)):

    # video_path = generate_output(video_data.url, video_data.video_length, video_data.voice_type)

    # video_path = f"/static/videos/{video_data.url.split('/')[-1]}_{video_data.video_length}_{video_data.voice_type}.mp4"
    # video_path_internal = f"static/videos/{video_data.url.split('/')[-1]}_{video_data.video_length}_{video_data.voice_type}.mp4"
    video_folder = "static/videos/"
    video_extension = ".mp4"

    video_files = [f for f in os.listdir(video_folder) if f.endswith(video_extension)]
    next_count = max([int(f.split('.')[0]) for f in video_files], default=0) + 1
    new_video_name = f"{next_count:04d}{video_extension}"

    video_link = f"https://{hostname}:8000/static/videos/{new_video_name}"
    video_path = os.path.join(video_folder, new_video_name)

    # background_tasks.add_task(delete_video_after_delay, video_path, 60)

    return_data = generate_url_video_and_social_mendia_post(video_data.url, video_data.video_width, video_data.video_height, video_data.video_length, video_data.voice_type, video_data.language_code, video_path)

    return {"video_path": video_link, "social_media_post":return_data}

@app.post("/generate_prompt_video_and_social_media_post", response_model=VideoOutput)
def generate_prompt_video_and_social_mendia_post_endpoint(video_data: prompt_VideoInput, background_tasks: BackgroundTasks, token: str = Depends(get_current_user)):

    # video_path = generate_output(video_data.url, video_data.video_length, video_data.voice_type)

    # video_path = f"/static/videos/{video_data.prompt.split('/')[-1]}_{video_data.video_length}_{video_data.voice_type}.mp4"
    # video_path_internal = f"static/videos/{video_data.prompt.split('/')[-1]}_{video_data.video_length}_{video_data.voice_type}.mp4"

    video_folder = "static/videos/"
    video_extension = ".mp4"

    video_files = [f for f in os.listdir(video_folder) if f.endswith(video_extension)]
    next_count = max([int(f.split('.')[0]) for f in video_files], default=0) + 1
    new_video_name = f"{next_count:04d}{video_extension}"

    video_link = f"https://{hostname}:8000/static/videos/{new_video_name}"
    video_path = os.path.join(video_folder, new_video_name)

    # background_tasks.add_task(delete_video_after_delay, video_path, 60)

    return_data = generate_prompt_video_and_social_mendia_post(video_data.prompt, video_data.video_width, video_data.video_height, video_data.video_length, video_data.voice_type, video_data.language_code, video_path)

    return {"video_path": video_link, "social_media_post":return_data}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
