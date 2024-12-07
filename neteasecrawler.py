from src.lib import db
from src.cli import cli

if __name__ == "__main__":
    try:
        cli()
    finally:
        db.save()
