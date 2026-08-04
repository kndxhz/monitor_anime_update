# /usr/bin/env python3

import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
PROXIES = {
    "http": os.getenv("PROXIES", "http://127.0.0.1:7890"),
    "https": os.getenv("PROXIES", "http://127.0.0.1:7890"),
}
IDS = os.getenv("IDS", "").split(",")


def main():

    for id in IDS:
        episodes = get_episodes(id, type="TV", limit=100, offset=0)
        print(episodes)


def get_episodes(subject_id, type=None, limit=None, offset=None):
    url = f"https://api.bgm.tv/v0/episodes?subject_id={subject_id}"
    if type:
        url += f"&type={type}"
    if limit:
        url += f"&limit={limit}"
    if offset:
        url += f"&offset={offset}"

    payload = {}
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "kndxhz/monitor_anime_update (https://github.com/kndxhz/monitor_anime_update)",
    }

    response = requests.request(
        "GET", url, headers=headers, data=payload, proxies=PROXIES
    )

    return response.json()


if __name__ == "__main__":
    main()
