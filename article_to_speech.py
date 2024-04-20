from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import pydub
import warnings

SUBSTACK_URL = "https://www.richardhanania.com/p/if-scott-alexander-told-me-to-jump"

warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_article_text(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    body_markup = soup.find(class_="body markup")
    if not body_markup:
        raise ValueError("The specified class 'body markup' was not found in the HTML.")

    text_elements = body_markup.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]
    )
    text = " ".join(element.get_text() for element in text_elements)
    return text


def split_text(text, limit=4096):
    words = text.split()
    current_length = 0
    chunk = []
    for word in words:
        current_length += len(word) + 1  # Include space in length calculation
        if current_length > limit:
            yield " ".join(chunk)
            chunk = [word]
            current_length = len(word) + 1
        else:
            chunk.append(word)
    yield " ".join(chunk)


def call_api_and_save_audio(chunks):
    client = OpenAI(api_key=OPENAI_API_KEY)
    combined_audio = pydub.AudioSegment.silent(duration=0)

    for idx, chunk in enumerate(chunks):
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=chunk,
                speed=1.1,
            )
            audio_path = f"temp_output_{idx}.mp3"
            response.stream_to_file(audio_path)
            audio_segment = pydub.AudioSegment.from_mp3(audio_path)
        except Exception as api_err:
            raise ValueError(
                f"Failed to create or retrieve audio for chunk {idx}: {api_err}"
            )

        duration_seconds = len(audio_segment) / 1000
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        print(
            f"Duration of segment {idx}: {int(minutes)} minutes and {seconds:.2f} seconds"
        )

        combined_audio += audio_segment
        os.remove(audio_path)  # Clean up the temp file

    combined_audio.export("output.mp3", format="mp3")


def main():
    url = SUBSTACK_URL

    try:
        article_text = get_article_text(url)
        chunks = list(split_text(article_text))
        call_api_and_save_audio(chunks)
        print("Audio file created successfully.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
