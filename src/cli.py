from getpass import getpass

import click

from .azuracast import *
from .lib import *


def try_index(lst: list, value):
    try:
        return lst.index(value)
    except ValueError:
        return -1


@click.group()
@click.option("--api-delay", help="API delay", default=0.1, type=float)
def cli(api_delay: float):
    global api_deplay
    api_deplay = api_delay


def music():
    @cli.group()
    def music():
        pass

    @music.command()
    def list():
        """List all musics."""
        for music_id, music in db.musics.items():
            print(f"{music_id} - {music.get_std_name()}")

    @music.command()
    @click.option("--id", help="Music id to search for.", type=int)
    @click.option("--name", help="Music name to search for.")
    @click.option("--fuzzy", help="Fuzzy search.", is_flag=True)
    def search(id: int | None, name: str | None, fuzzy: bool):
        """Search musics by id or name."""
        if id is None and name is None:
            raise click.UsageError("id or name must be specified")
        for music_id, music_name in search_music(id=id, name=name, fuzzy=fuzzy):
            print(f"{music_id} - {music_name}")

    @music.command()
    @click.option("--id", help="Music id to search in playlist.", type=int)
    @click.option("--name", help="Music name to search in playlist.")
    @click.option("--fuzzy", help="Fuzzy search.", is_flag=True)
    def search_in_playlists(id: int | None, name: str | None, fuzzy: bool):
        """Search musics in playlist by id or name."""
        if id is None and name is None:
            raise click.UsageError("id or name must be specified")
        for p_id, p_name, m_id, m_name in search_music_in_playlists(id=id, name=name, fuzzy=fuzzy):
            print(f"music: {m_id} - {m_name}")
            print(f"  playlist: {p_id} - {p_name}")


def playlist():
    @cli.group()
    def playlist():
        pass

    @playlist.command()
    @click.option("--user-id", help="User id to list playlist.")
    @click.option("--user-name", help="User name to list playlist.")
    def list(user_id: str | None, user_name: str | None):
        """List all playlists."""
        if user_name is not None:
            user_ids = [k for k, v in db.users.items() if v.name == user_name]
            if not user_ids:
                raise click.UsageError("user not found")
            user_id = user_ids[0]
        playlists = map(int, db.playlists.keys())
        if user_id is not None:
            user_playlists = db.users.get(user_id, User()).playlists
            playlists = sorted(set(playlists).intersection(user_playlists), key=user_playlists.index)
        for playlist_id in playlists:
            print(f"{playlist_id} - {db.playlists[str(playlist_id)].name}")

    @playlist.command()
    @click.option("--all", help="Pull all playlist.", is_flag=True)
    @click.option("--download", help="Download playlist.", is_flag=True)
    @click.option("--id", help="Playlist id to pull.", type=int)
    @click.option("--name", help="Playlist name to pull.")
    @click.option("--fuzzy", help="Fuzzy search.", is_flag=True)
    def pull(id: int | None, name: str | None, download: bool, all: bool, fuzzy: bool):
        """Pull playlist by id or name."""
        if all:
            Crawler.open().pull_all_playlist(download=download)
            return
        if id is None and name is None:
            raise click.UsageError("id or name must be specified")
        for playlist_id, _ in search_playlist(id=id, name=name, fuzzy=fuzzy):
            Crawler.open().pull_playlist(playlist_id, download=download)

    @playlist.command()
    @click.option("--id", help="Playlist id to search for.", type=int)
    @click.option("--name", help="Playlist name to search for.")
    @click.option("--fuzzy", help="Fuzzy search.", is_flag=True)
    def search(id: int | None, name: str | None, fuzzy: bool):
        """Search playlists by id or name."""
        if id is None and name is None:
            raise click.UsageError("id or name must be specified")
        for playlist_id, playlist_name in search_playlist(id=id, name=name, fuzzy=fuzzy):
            print(f"{playlist_id} - {playlist_name}")

    @playlist.command()
    @click.option("--id", help="Playlist id to search for and build.", type=int)
    @click.option("--name", help="Playlist name to search for and build.")
    @click.option("--list-builded", help="List all builded playlists.", is_flag=True)
    @click.option("--sort-by", help="Sort playlist by userid.", type=str)
    def build(id: int | None, name: str | None, list_builded: bool, sort_by: str | None):
        """Build playlists by name."""
        if list_builded:
            dist_playlists = DIST_DIR.iterdir()
            if sort_by is not None:
                user_playlists = db.users.get(sort_by, User()).playlists
                dist_playlists = sorted(dist_playlists, key=lambda fp: try_index(user_playlists, int(fp.stem)))
            dist_playlists = [i for i in dist_playlists]
            for fp in dist_playlists:
                print(f"{fp.relative_to(BASE_DIR)} - {db.playlists[fp.stem]}")
            return

        if id is None and name is None:
            raise click.UsageError("id or name must be specified")
        for fp, _ in search_playlist(id=id, name=name):
            build_playlist(fp)


def user():
    @cli.group()
    def user():
        pass

    @user.command()
    def list():
        """List all users."""
        for user_id, user in db.users.items():
            print(f"{user_id} - {user.name}")


def azuracast():
    @cli.group()
    def azuracast():
        pass

    @azuracast.command()
    @click.argument("playlist-id")
    @click.option("--host", help="Host.", required=True)
    @click.option("--port", help="Port.", default=2022, type=int)
    @click.option("--username", help="Username.", required=True)
    def sync(playlist_id: str, host: str, port: int, username: str):
        """Sync playlist to azuracast."""
        playlist = db.playlists[playlist_id]

        sftp = connect_azura_sftp(host, port, username, getpass())

        filenames = set(sftp.listdir())
        if playlist.name not in filenames:
            sftp.mkdir(playlist.name)
        sftp.chdir(playlist.name)

        filenames = set(sftp.listdir())
        musics = [db.musics[str(i)] for i in playlist.music_ids]
        for music in musics:
            dist_fp = music.get_dist_path(playlist_id)
            if not dist_fp.exists():
                warnings.warn(f"Music {dist_fp.name} not found.")
                continue
            print(f"Uploading: {dist_fp.name} - {music.get_std_name()} ...")
            if dist_fp.name in filenames:
                if sftp.stat(dist_fp.name).st_size == dist_fp.stat().st_size:
                    print("Already up to date.")
                    continue
            sftp.put(dist_fp, dist_fp.name)
            print("Done.")

        for filename in filenames.difference(i.get_dist_name() for i in musics):
            print(f"Removing: {filename} ...")
            sftp.remove(filename)
            print("Done.")


music()
playlist()
user()
azuracast()
