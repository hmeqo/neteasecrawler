import sys


def neteasecrawler():
    from project.cli import cli
    from project.lib import db

    try:
        cli()
    finally:
        db.save()
