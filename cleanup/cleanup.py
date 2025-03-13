# cleanup\cleanup.py
import os
import time
import logging
import docker
from sqlalchemy import create_engine, MetaData, Table
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

client = docker.from_env()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
metadata = MetaData()

models_table = Table('models', metadata, autoload_with=engine, extend_existing=True)

def cleanup_docker_containers():
    logger.info("Cleaning up Docker containers older than 30 days...")
    thirty_days_ago = datetime.now() - timedelta(days=30)
    for container in client.containers.list(all=True):
        try:
            created_at = isoparse(container.attrs['Created'])
            if created_at < thirty_days_ago:
                logger.info(f"Removing container {container.name} (created on {created_at})")
                container.remove(force=True)
        except Exception as e:
            logger.error(f"Error processing container {container.name}: {e}")

def cleanup_old_models_in_db():
    logger.info("Cleaning up old models from the database...")
    thirty_days_ago = datetime.now() - timedelta(days=30)
    with engine.connect() as conn:
        result = conn.execute(models_table.delete().where(models_table.c.created_at < thirty_days_ago))
        logger.info(f"Deleted {result.rowcount} old model records from the database.")

def run_cleanup():
    while True:
        try:
            cleanup_docker_containers()
            cleanup_old_models_in_db()
        except Exception as e:
            logger.error(f"Error during cleanup: %s", e)
        time.sleep(43200)

if __name__ == "__main__":
    run_cleanup()