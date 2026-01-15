import json
import zipfile
from functools import partial
from itertools import repeat
from multiprocessing.pool import ThreadPool
from pathlib import Path
from shutil import rmtree
from traceback import print_exc
import pandas as pd
from time import sleep
from urllib.parse import urlparse
import httpx
from loguru import logger
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

ROOT = Path(__file__).resolve().parent

__HEADERS__ = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
}

__CHUNK_SIZE__ = 1024 * 10

__THREAD_NUM__ = 2

__PROXY__ = None


def init_contents(retry=3):
    CONTENTS_URL = "https://flk.npc.gov.cn/law-search/highSearch/highSearch"
    data = {
        "dataList": [
            {
                "fieldName": "flfg_code_id",
                "values": [100, 110, 120, 130, 140, 150, 160, 170, 200, 195],
                "link": 0,
                "searchType": 1,
                "index": 0,
            }
        ],
        "orderByParam": {},
        "pageNum": 1,
        "pageSize": 1000,
    }
    BATCH_URL = "https://flk.npc.gov.cn/law-search/download/batch"

    try:
        with httpx.Client(headers=__HEADERS__, proxy=__PROXY__) as client:
            response = client.post(CONTENTS_URL, json=data)
            if response.status_code != 200:
                raise Exception(f"Failed to download contents: {response.status_code}")
            contents = response.json()
            if not contents["code"] == 200:
                raise Exception("Failed to download contents")
            logger.info(f"Contents downloaded with msg {contents['msg']}")
            batch_resp = client.post(
                BATCH_URL,
                json=[{"bbbs": c["bbbs"], "format": "docx"} for c in contents["rows"]],
            )
            logger.info(f"Batch meta data fetched with msg {batch_resp.json()['msg']}")
            return batch_resp.json()["data"]
    except Exception as e:
        print_exc()
        return e


def download_item(args, retry=3):
    client, row, dir = args
    url = row["url"]
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')
    filename = path_parts[-1]
    file_path = dir / filename
    tmp_path = dir / f"{filename}.tmp"

    if file_path.is_file():
        return file_path
    if tmp_path.is_file():
        tmp_path.unlink()

    while retry > 0:
        retry -= 1
        try:
            with client.stream("GET", url) as response:

                if response.status_code != 200:
                    raise Exception(f"Failed to download file: {response.status_code}")

                with open(tmp_path, "wb") as f:
                    for chunk in response.iter_bytes(__CHUNK_SIZE__):
                        f.write(chunk)

            file_path.unlink(missing_ok=True)
            tmp_path.rename(file_path)
            return file_path
        except Exception as e:
            print_exc()
            logger.error(f"Failed to download file: {e}")


def main():
    contents = init_contents()
    assert isinstance(contents, list), contents
    JSON_DOCUMENTS_DIR = ROOT / "data_cn_partial" / "documents"
    JSON_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    # contents (dict) to dataframe and store csv
    df = pd.DataFrame(contents)
    df.to_csv(JSON_DOCUMENTS_DIR.parent / "index.csv", index=False)

    pool = ThreadPool(__THREAD_NUM__)

    with Progress(
        TextColumn("[bold blue]Converting xml to json:", justify="right"),
        TextColumn("•"),
        "[progress.percentage]•[{task.completed}/{task.total}]",  # Percentage
        TextColumn("•"),
        BarColumn(bar_width=None),
        TextColumn("•"),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    ) as __FILE_PROGRESS__:

        with httpx.Client(headers=__HEADERS__, proxy=__PROXY__) as client:
            results = pool.imap(
                download_item,
                zip(
                    repeat(client),
                    contents,
                    repeat(JSON_DOCUMENTS_DIR),
                ),
            )

            task_id = __FILE_PROGRESS__.add_task(
                "convert",
                total=len(contents),
            )
            for result in results:
                if isinstance(result, Path):
                    __FILE_PROGRESS__.update(task_id, advance=1)

            __FILE_PROGRESS__.stop_task(task_id)

            logger.info(f"Download {len(contents)} files")


if __name__ == "__main__":

    main()
