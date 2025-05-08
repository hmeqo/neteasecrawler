import datetime as dt
import json
import shutil
import time
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx
import music_tag
from DrissionPage import Chromium
from pyncm import apis

BASE_DIR = Path(__file__).parent.parent.parent / "neteasecloudmusic"
INFOS_DIR = BASE_DIR / "infos"
LYRICS_DIR = BASE_DIR / "lyrics"
MUSICS_DIR = BASE_DIR / "musics"
DIST_DIR = BASE_DIR / "dist"

BASE_DIR.mkdir(parents=True, exist_ok=True)
INFOS_DIR.mkdir(parents=True, exist_ok=True)
LYRICS_DIR.mkdir(parents=True, exist_ok=True)
MUSICS_DIR.mkdir(parents=True, exist_ok=True)
DIST_DIR.mkdir(parents=True, exist_ok=True)

MUSICS_DB_FILE = BASE_DIR / "musics.json"
PLAYLISTS_DB_FILE = BASE_DIR / "playlists.json"
USERS_DB_FILE = BASE_DIR / "users.json"

api_delay = 0.1


@dataclass
class Music:
    name: str = ""
    id: int = 0
    pst: int = 0
    t: int = 0
    ar: dict = field(default_factory=dict)
    alia: list = field(default_factory=list)
    pop: float = 0.0
    st: int = 0
    rt: str = ""
    fee: int = 0
    v: int = 0
    crbt: Any | None = None
    cf: str = ""
    al: dict = field(default_factory=dict)
    dt: int = 0  # noqa: F811
    h: dict = field(default_factory=dict)
    m: dict = field(default_factory=dict)
    l: dict = field(default_factory=dict)  # noqa: E741
    sq: dict = field(default_factory=dict)
    hr: Any | None = None
    a: Any | None = None
    cd: str = ""
    no: int = 0
    rtUrl: Any | None = None
    ftype: int = 0
    rtUrls: list[str] = field(default_factory=list)
    djId: int = 0
    copyright: int = 0
    s_id: int = 0
    mark: int = 0
    originCoverType: int = 0
    originSongSimpleData: Any | None = None
    tagPicList: Any | None = None
    resourceState: int = 0
    version: int = 0
    songJumpInfo: Any | None = None
    entertainmentTags: Any | None = None
    displayTags: Any | None = None
    awardTags: Any | None = None
    single: int = 0
    noCopyrightRcmd: Any | None = None
    mv: int = 0
    rtype: int = 0
    rurl: Any | None = None
    mst: int = 0
    cp: int = 0
    publishTime: int = 0
    tns: list[str] = field(default_factory=list)

    @property
    def artist(self):
        return " & ".join(map(lambda x: x["name"], self.ar))

    @property
    def album(self):
        return self.al["name"]

    @property
    def year(self):
        return dt.date.fromtimestamp(self.publishTime / 1000).year

    @property
    def album_pic_url(self):
        return self.al["picUrl"]

    def get_std_name(self, reverse=False):
        return f"{self.name} - {self.artist}" if reverse else f"{self.artist} - {self.name}"

    def get_dist_name(self):
        return f"{self.id}.mp3"

    def get_dist_path(self, dirname: int | str):
        return DIST_DIR / f"{dirname}" / self.get_dist_name()

    def get_download_name(self):
        return f"{self.id}.mp3"

    def get_download_path(self):
        return MUSICS_DIR / self.get_download_name()


@dataclass
class User:
    id: int = 0
    name: str = ""
    playlists: list[int] = field(default_factory=list)


@dataclass
class Playlist:
    id: int = 0
    name: str = ""
    description: str | None = None
    createTime: int = 0
    music_ids: list[int] = field(default_factory=list)


class DB:
    def __init__(self):
        self.musics: dict[str, Music] = {k: Music(**v) for k, v in json.loads(MUSICS_DB_FILE.read_text()).items()}
        self.playlists: dict[str, Playlist] = {
            k: Playlist(**v) for k, v in json.loads(PLAYLISTS_DB_FILE.read_text()).items()
        }
        self.users: dict[str, User] = {k: User(**v) for k, v in json.loads(USERS_DB_FILE.read_text()).items()}

    def save(self):
        MUSICS_DB_FILE.write_text(
            json.dumps({k: asdict(v) for k, v in self.musics.items()}, indent=4, ensure_ascii=False)
        )
        PLAYLISTS_DB_FILE.write_text(
            json.dumps({k: asdict(v) for k, v in self.playlists.items()}, indent=4, ensure_ascii=False)
        )
        USERS_DB_FILE.write_text(
            json.dumps({k: asdict(v) for k, v in self.users.items()}, indent=4, ensure_ascii=False)
        )


def is_vip(music_info: dict):
    return music_info["freeTrialInfo"] is not None


def not_vip(music_info: dict):
    return music_info["freeTrialInfo"] is None


class Crawler:
    def __init__(self):
        self.browser = Chromium()

        tab = self.browser.latest_tab
        if isinstance(tab, str):
            print(tab)
            raise Exception
        self.tab = tab

    @staticmethod
    def get_details(music_id: int, update=False):
        """获取歌曲详情"""
        music = db.musics.get(str(music_id))
        if not update and music:
            return True, music
        details: dict = apis.track.GetTrackDetail([music_id])  # type: ignore
        time.sleep(api_delay)
        if not details.get("code", 0) == 200:
            return False, details
        details = details["songs"][0]
        music = Music(**details)
        db.musics[str(music_id)] = music
        return True, music

    @staticmethod
    def get_lyrics(music_id: int):
        """获取歌词"""
        lyrics_file = LYRICS_DIR / f"{music_id}.json"
        lyrics: dict = apis.track.GetTrackLyricsNew(music_id)  # type: ignore
        time.sleep(api_delay)
        if not lyrics.get("code", 0) == 200:
            return False, lyrics
        lyrics_file.write_text(json.dumps(lyrics, indent=4, ensure_ascii=False))
        return True, lyrics

    @classmethod
    def open(cls):
        crawler = cls()
        if not crawler.login():
            raise Exception("Login failed.")
        return crawler

    def _download(self, music_id: int):
        """下载歌曲"""
        info_file = INFOS_DIR / f"{music_id}.json"
        music_file = MUSICS_DIR / f"{music_id}.mp3"

        info: dict = apis.track.GetTrackAudioV1([music_id])  # type: ignore
        time.sleep(api_delay)
        if not info.get("code", 0) == 200:
            return False, info
        info = info["data"][0]

        if music_file.exists() and info_file.exists():
            old_info = json.loads(info_file.read_text())
            if not_vip(old_info) and is_vip(info) or info["freeTrialInfo"] == old_info["freeTrialInfo"]:
                return None, old_info

        info_file.write_text(json.dumps(info, indent=4, ensure_ascii=False))
        for _ in range(3):
            status, _ = self.tab.download.download(
                info["url"],
                music_file.parent,
                music_file.name,
                file_exists="overwrite",
            )
            if status == "success":
                break
            print("Failed. Retrying...")
            # print(f"Downloading: {info["url"]} -> {music_file.relative_to(BASE_DIR)}", end="\t")
            # try:
            #     res = httpx.get(info["url"], headers={"Referer": "https://music.163.com/"})
            # except Exception as e:
            #     print(e)
            #     continue
            # if res.status_code == 200:
            #     music_file.write_bytes(res.content)
            #     print("Downloaded.")
            #     break
            # else:
            #     print(f"Failed. (status code: {res.status_code})")
        else:
            warnings.warn(f"Failed to download: {info['url']}")
        return True, info

    def login(self):
        """网页版登录"""
        if not str(self.tab.url).startswith("https://music.163.com/"):
            self.tab.get("https://music.163.com")
        print("Waiting for login...")
        if not self.tab.wait.eles_loaded("xpath=//div[@class='m-tophead f-pr j-tflag']//img", timeout=180):
            print("Timeout.")
            return False
        print("Login success.")
        cookies = dict((i["name"], i["value"]) for i in self.tab.cookies())
        apis.login.LoginViaCookie(cookies["MUSIC_U"])
        time.sleep(api_delay)
        return True

    def download_music(self, music_id: int):
        print("Downloading:", music_id)
        status, music_info = self._download(music_id)
        if status is True:
            print("Downloaded.")
        elif status is False:
            print(music_info)
            print("Failed.")
        elif status is None:
            print("Already downloaded.")

    def pull_playlist(self, playlist_id: int, download=False, update_details=False):
        """获取歌单信息, 指定参数可下载"""
        # self.tab.get(f"https://music.163.com/#/my/m/music/playlist?id={playlist_id}")
        info: dict = apis.playlist.GetPlaylistInfo(playlist_id)["playlist"]  # type: ignore
        time.sleep(api_delay)

        # playlist_name: str = self.tab.ele("xpath=//h2[@class='f-ff2 f-thide']").text  # type: ignore
        playlist_name = info["name"]

        # music_ids = [i.attr("data-res-id") for i in list(self.tab.eles("xpath=//table/tbody/tr/td[1]//span[1]"))]
        musics: list[tuple[int, str]] = [
            (i["id"], i["name"])
            for i in apis.playlist.GetPlaylistAllTracks(playlist_id)["songs"]  # type: ignore
        ]
        time.sleep(api_delay)

        playlist = Playlist(
            id=playlist_id,
            name=playlist_name.replace("\xa0", " "),
            description=info["description"],
            createTime=info["createTime"],
            music_ids=[i[0] for i in musics],
        )

        db.playlists[str(playlist_id)] = playlist

        for music_id, music_name in musics:  # type: ignore
            print(f"Getting music details: {music_id} - {music_name}", end="\t")
            status, _ = self.get_details(music_id, update=update_details)
            if status is True:
                print("Success.")
            else:
                print("Failed.")

            if download:
                self.download_music(music_id)
        return playlist

    def pull_all_playlist(self, download=False, update_details=False):
        """获取所有歌单信息, 指定参数可下载"""
        if not str(self.tab.url).startswith("https://music.163.com/#/my/m/music/playlist"):
            my_music = self.tab.ele("xpath=//ul[@class='m-nav j-tflag']/li[2]")
            my_music.click()  # type: ignore
            self.tab.wait.eles_loaded("xpath=//a[@class='s-fc7']")

        playlist: list[tuple[int, str]] = [
            (int(i.attr("data-matcher").replace("playlist-", "", 1)), i.ele("xpath=//p[@class='name f-thide']").text)
            for i in list(self.tab.eles("xpath=//ul[@class='j-flag f-cb']/li"))
        ]

        user_ele = self.tab.ele("xpath=//a[@class='s-fc7']")
        userid: str = str(user_ele.attr("href")).split("id=", 1)[-1]
        username: str = str(user_ele.text)
        user = User(id=int(userid), name=username, playlists=[playlist_id for playlist_id, _ in playlist])
        db.users[userid] = user

        for playlist_id, playlist_name in playlist:
            print(f"Pulling playlist: {playlist_id} - {playlist_name} ...")
            self.pull_playlist(playlist_id, download=download, update_details=update_details)
            print("Done.")


def build_playlist(playlist_id: int, pull_lyrics=False, update_lyrics=False, update_artwork=False):
    """从歌单生成mp3文件 (包含专辑封面等信息)"""
    musics = [db.musics[str(i)] for i in set(db.playlists[str(playlist_id)].music_ids)]
    build_musics(
        musics, playlist_id, pull_lyrics=pull_lyrics, update_lyrics=update_lyrics, update_artwork=update_artwork
    )


def build_musics(musics: list[Music], dirname: int | str, pull_lyrics=False, update_lyrics=False, update_artwork=False):
    for music in musics:
        music_fp = music.get_download_path()
        if not music_fp.exists():
            warnings.warn(f"Music {music_fp.name} not found.")
            continue
        dist_fp = music.get_dist_path(dirname)
        dist_fp.parent.mkdir(parents=True, exist_ok=True)

        print(f"Building: {music.id} -> {dist_fp.relative_to(BASE_DIR)} ...", end="\t")
        if not dist_fp.exists():
            shutil.copy(music_fp, dist_fp)

        f = music_tag.load_file(dist_fp)
        if not f:
            raise Exception(f"Failed to load {dist_fp}.")

        f["title"] = music.name
        f["artist"] = music.artist
        f["album"] = music.album
        f["year"] = music.year
        if pull_lyrics and (update_lyrics or not f["lyrics"]):
            status, lyrics = Crawler.get_lyrics(music.id)
            time.sleep(api_delay)
            if not status:
                raise Exception(f"Failed to get lyrics for {music.name}.")
            f["lyrics"] = lyrics["lrc"]["lyric"]
        if update_artwork or not f["artwork"]:
            response = httpx.get(music.album_pic_url)
            time.sleep(api_delay)
            if not response.is_success:
                raise Exception(f"Failed to get album cover for {music.name}.")
            f["artwork"] = response.content

        print("Done.")
        f.save()

    for i in set((DIST_DIR / f"{dirname}").iterdir()).difference(m.get_dist_path(dirname) for m in musics):
        print(f"Removing: {i.relative_to(BASE_DIR)} ...")
        i.unlink()
        print("Done.")


def find_playlist(*, id: int | None = None, name: str | None = None, fuzzy: bool = False):
    """本地查询, 搜索歌单"""
    p_id = None if id is None else str(id)
    for playlist_id, playlist in db.playlists.items():
        if p_id is not None and p_id == playlist_id:
            yield int(playlist_id), playlist.name
            break
        if name is not None and (name.lower() in playlist.name.lower() if fuzzy else name == playlist.name):
            yield int(playlist_id), playlist.name


def find_music(*, id: int | None = None, name: str | None = None, fuzzy: bool = False):
    """本地查询, 搜索歌曲"""
    m_id = None if id is None else str(id)
    for music_id, music in db.musics.items():
        if m_id is not None and m_id == music_id:
            yield int(music_id), music.get_std_name()
            break
        if name is not None and (
            name.lower() in music.get_std_name().lower()
            if fuzzy
            else name == music.name or name == music.get_std_name()
        ):
            yield int(music_id), music.get_std_name()


def find_music_in_playlists(*, id: int | None = None, name: str | None = None, fuzzy: bool = False):
    """查询一首歌存在于哪些歌单"""
    musics = find_music(name=name, fuzzy=fuzzy)
    music_ids = {id} if name is None else {i[0] for i in musics}
    for playlist_id, playlist in db.playlists.items():
        ids = music_ids.intersection(playlist.music_ids)
        if ids:
            yield from (
                (int(playlist_id), playlist.name, music_id, db.musics[str(music_id)].get_std_name()) for music_id in ids
            )


db = DB()
