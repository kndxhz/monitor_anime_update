# /usr/bin/env python3

import json
import datetime
import sqlite3
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


class EpisodeUpdateInfo:
    __tablename__ = "episode_update_info"

    def __init__(self, subject_id, now_episode, update_time):
        self.subject_id = subject_id
        self.now_episode = now_episode
        self.update_time = update_time


def init_db():
    conn = sqlite3.connect("episode_update_info.db")
    cursor = conn.cursor()
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {EpisodeUpdateInfo.__tablename__} (
            subject_id INTEGER PRIMARY KEY,
            now_episode INTEGER,
            update_time TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def main():

    for id in IDS:
        episodes = get_episodes(id)
        json_episodes = json.dumps(episodes, ensure_ascii=False, indent=4)
        print(f"Subject ID: {id}")
        print(json_episodes)


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
    init_db()
    main()
