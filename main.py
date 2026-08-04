# /usr/bin/env python3

import datetime
import os

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


load_dotenv()

API_KEY = os.getenv("API_KEY")
PROXIES = {
    "http": os.getenv("PROXIES", "http://127.0.0.1:7890"),
    "https": os.getenv("PROXIES", "http://127.0.0.1:7890"),
}
IDS = os.getenv("IDS", "").split(",")
engine = create_engine("sqlite:///episode_update_info.db")


class Base(DeclarativeBase):
    pass


class EpisodeUpdateInfo(Base):
    __tablename__ = "episode_update_info"

    subject_id: Mapped[int] = mapped_column(primary_key=True)
    now_episode: Mapped[int | None]
    next_update_time: Mapped[str | None]


def init_db():
    Base.metadata.create_all(engine)


def main():
    with Session(engine) as session:
        for id in IDS:
            episodes = get_episodes(id)
            print(f"Subject ID: {id}")
            now = datetime.datetime.now(datetime.UTC)
            now_date = now.strftime("%Y-%m-%d")
            aired_episodes = [
                episode
                for episode in episodes["data"]
                if episode.get("airdate") and episode["airdate"] <= now_date
            ]
            upcoming_episodes = [
                episode
                for episode in episodes["data"]
                if episode.get("airdate") and episode["airdate"] > now_date
            ]
            current_episode = max(
                aired_episodes,
                key=lambda episode: (episode["airdate"], episode["sort"]),
                default=None,
            )
            next_episode = min(
                upcoming_episodes,
                key=lambda episode: (episode["airdate"], episode["sort"]),
                default=None,
            )

            update_info = session.get(EpisodeUpdateInfo, int(id))
            if update_info is None:
                session.add(
                    EpisodeUpdateInfo(
                        subject_id=int(id),
                        now_episode=(
                            int(current_episode["sort"]) if current_episode else None
                        ),
                        next_update_time=(
                            next_episode["airdate"] if next_episode else None
                        ),
                    )
                )
                session.commit()

            for episode in episodes["data"]:
                if episode["airdate"] == now_date:
                    print(
                        f"Episode {episode['sort']} of Subject ID {id} is airing today!"
                    )
                    break


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
