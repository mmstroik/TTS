import requests
from bs4 import BeautifulSoup
import os
import pydub
import aiohttp
import asyncio
from dotenv import load_dotenv
import warnings
import logging

SUBSTACK_URL = "https://www.richardhanania.com/p/if-scott-alexander-told-me-to-jump"

warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_article_text(url):
    logger.info(f"Getting article text from: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    title = soup.find("title").text.strip()
    file_name = "output/" + "_".join(title.split()).lower() + ".mp3"
    
    body_markup = soup.find(class_="body markup")
    if not body_markup:
        body_markup = soup.find(class_="content-area primary")
    if not body_markup:
        body_markup = soup.find(class_="InlineReactSelectionWrapper-root")
    if not body_markup:
        raise ValueError("The specified class was not found in the HTML.")

    text = "\n".join(element.get_text() for element in body_markup.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]
    ))
    logger.info(f"Successfully extracted text from {url}")
    return text, file_name


def split_text_by_paragraphs(text):
    paragraphs = text.split("\n")
    # Remove empty paragraphs
    paragraphs = [p for p in paragraphs if p.strip()]
    return paragraphs


async def fetch_audio(session, chunk, idx, api_key):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "tts-1",
        "voice": "alloy",
        "input": chunk,
        "speed": 1.1,
    }

    async with session.post(url, json=payload, headers=headers) as response:
        if response.status != 200:
            raise ValueError(f"Failed to create or retrieve audio for chunk {idx}: {await response.text()}")
        
        audio_path = f"output/temp_output_{idx}.mp3"
        with open(audio_path, 'wb') as f:
            while True:
                chunk = await response.content.read(1024)
                if not chunk:
                    break
                f.write(chunk)

        audio_segment = pydub.AudioSegment.from_mp3(audio_path)
        os.remove(audio_path)  # Clean up the temp file
        return audio_segment


async def call_api_and_save_audio(chunks, api_key, file_name):
    combined_audio = pydub.AudioSegment.silent(duration=0)
    pause_duration = 350  # milliseconds of silence

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_audio(session, chunk, idx, api_key) for idx, chunk in enumerate(chunks)]
        audio_segments = await asyncio.gather(*tasks)

    for idx, audio_segment in enumerate(audio_segments):
        duration_seconds = len(audio_segment) / 1000
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        print(
            f"Duration of segment {idx}: {int(minutes)} minutes and {seconds:.2f} seconds"
        )
        combined_audio += audio_segment
        combined_audio += pydub.AudioSegment.silent(duration=pause_duration)  # pause between chunks

    combined_audio.export(file_name, format="mp3")


async def main():
    url = SUBSTACK_URL 
    api_key = OPENAI_API_KEY
    try:
        article_text, file_name = get_article_text(url)
        chunks = split_text_by_paragraphs(article_text)
        await call_api_and_save_audio(chunks, api_key, file_name)
        print("Audio file created successfully.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

