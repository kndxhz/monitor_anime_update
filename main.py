# /usr/bin/env python3

import datetime
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY")
PROXIES = {
    "http": os.getenv("PROXIES", "http://127.0.0.1:7890"),
    "https": os.getenv("PROXIES", "http://127.0.0.1:7890"),
}
IDS = os.getenv("IDS", "").split(",")
engine = create_engine("sqlite:///episode_update_info.db")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO", "").split(",")


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
        ids_set = {int(id) for id in IDS if id}
        db_ids = set(
            session.execute(select(EpisodeUpdateInfo.subject_id)).scalars().all()
        )
        orphan_ids = db_ids - ids_set
        if orphan_ids:
            session.execute(
                delete(EpisodeUpdateInfo).where(
                    EpisodeUpdateInfo.subject_id.in_(orphan_ids)
                )
            )
            session.commit()
            logger.info(f"已从数据库移除过期条目: {orphan_ids}")

        for id in IDS:
            episodes = get_episodes(id)
            logger.info(f"番剧 ID: {id}")
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

            # now_date = "2026-08-06"
            for episode in episodes["data"]:
                if episode["airdate"] == now_date:
                    # if True:
                    notify_user(id, episode, now_date)
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


def get_subject(subject_id):
    url = f"https://api.bgm.tv/v0/subjects/{subject_id}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": "kndxhz/monitor_anime_update (https://github.com/kndxhz/monitor_anime_update)",
    }
    response = requests.get(url, headers=headers, proxies=PROXIES)
    return response.json()


def notify_user(subject_id, episode, now_date):
    subject = get_subject(subject_id)
    subject_name = subject.get("name_cn") or subject.get("name") or f"番剧 {subject_id}"
    episode_sort = episode["sort"]

    logger.info(f"{subject_name} 第 {episode_sort} 集今日播出！")

    if not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        logger.warning("SMTP 未配置，跳过通知")
        return

    email_subject = f"[番剧更新] {subject_name} 第 {episode_sort} 集今日播出！"
    html_body = f"""\
<html>
  <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
    <h2 style="color: #e74c3c;">番剧更新提醒</h2>
    <p style="font-size: 16px;"><strong>{subject_name}</strong> 第 <strong>{episode_sort}</strong> 集今日（{now_date}）播出！</p>
    <a href="https://bgm.tv/subject/{subject_id}" style="display: inline-block; margin-top: 16px; padding: 10px 24px; background: #e74c3c; color: #fff; text-decoration: none; border-radius: 4px;">前往查看</a>
  </body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = email_subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)
    msg.attach(
        MIMEText(
            f"{subject_name} 第 {episode_sort} 集今日（{now_date}）播出！\nhttps://bgm.tv/subject/{subject_id}",
            "plain",
            "utf-8",
        )
    )
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        logger.info(f"通知已发送至 {EMAIL_TO}")
    except (smtplib.SMTPException, OSError) as e:
        logger.error(f"发送通知失败: {e}")


if __name__ == "__main__":
    init_db()
    main()
