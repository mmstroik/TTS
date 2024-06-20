import requests
from bs4 import BeautifulSoup

url = "https://www.richardhanania.com/p/if-scott-alexander-told-me-to-jump"


def get_article_text(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    body_markup = soup.find(class_="body markup")
    if not body_markup:
        raise ValueError("The specified class 'body markup' was not found in the HTML.")

    text = "\n".join(element.get_text() for element in body_markup.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]
    ))
    return text

text = get_article_text(url)
print(text)