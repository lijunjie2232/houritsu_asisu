import json
import zipfile
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path
from shutil import rmtree
from traceback import print_exc

import httpx
import xmltodict
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


async def continuous_download(
    client: httpx.AsyncClient,
    url: str,
    file_path: Path,
    tmp_path: Path,
    retry=3,
    *args,
    **kwargs,
) -> Path:
    """
    Continuously download a file from a URL.

    """
    file_info = await client.head(url)

    # Get the total file size from headers
    total_size = int(file_info.headers.get("content-length", 0))

    while retry >= 0:
        retry -= 1
        # Check if we have a partially downloaded file
        downloaded_size = 0
        if tmp_path.is_file():
            if tmp_path.stat().st_size <= total_size:
                downloaded_size = tmp_path.stat().st_size
            else:
                tmp_path.unlink()

        # Resume download from where it left off
        headers_with_range = __HEADERS__.copy()
        headers_with_range["Range"] = f"bytes={downloaded_size}-"

        with Progress(
            TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
            TextColumn("•"),
            BarColumn(bar_width=None),
            TextColumn("•"),
            DownloadColumn(),
            TextColumn("•"),
            TransferSpeedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
        ) as __NET_PROGRESS__:
            task_id = __NET_PROGRESS__.add_task(
                "download",
                filename=file_path.name,
                start=False,
                total=total_size,
            )
            try:
                with open(tmp_path, "ab") as f:
                    __NET_PROGRESS__.update(task_id, completed=downloaded_size)
                    __NET_PROGRESS__.start_task(task_id)
                    async with client.stream(
                        "GET",
                        url,
                        headers=headers_with_range,
                        *args,
                        **kwargs,
                    ) as response:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                            __NET_PROGRESS__.update(task_id, advance=len(chunk))
            except Exception as e:
                print_exc()
                logger.error(f"Error downloading file: {e}")
            finally:
                __NET_PROGRESS__.stop_task(task_id)

            if not tmp_path.is_file():
                continue
            if tmp_path.stat().st_size == total_size:
                # File is already completely downloaded
                tmp_path.rename(file_path)
                return file_path
            elif tmp_path.stat().st_size > total_size:
                tmp_path.unlink()


async def init_contents(root: Path, retry=3):
    CONTENTS_URL = (
        "https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true"
    )
    root.mkdir(exist_ok=True, parents=True)
    CONTENTS_FILE = root / "all_xml.zip"
    CONTENTS_TEMP = root / "all_xml.zip.tmp"
    CONTENTS_DIR = root / "all_xml"

    async def unzip(file: Path, dest: Path, overwrite=True):
        try:
            CONTENTS_DIR.mkdir(parents=True, exist_ok=overwrite)
            with zipfile.ZipFile(CONTENTS_FILE, "r") as zip_ref:
                zip_ref.extractall(CONTENTS_DIR)
            return CONTENTS_DIR
        except Exception as e:
            if CONTENTS_DIR.is_dir():
                rmtree(CONTENTS_DIR)
            raise e

    while not CONTENTS_DIR.is_dir():
        if retry == 0:
            raise Exception("Failed to download contents")
        retry -= 1
        try:
            if not CONTENTS_FILE.is_file():
                logger.info("Downloading contents")
                async with httpx.AsyncClient(headers=__HEADERS__) as client:
                    assert CONTENTS_FILE == await continuous_download(
                        client,
                        CONTENTS_URL,
                        CONTENTS_FILE,
                        CONTENTS_TEMP,
                    ), Exception("Failed to download contents")
                    logger.info("Contents downloaded")
            assert CONTENTS_DIR == await unzip(CONTENTS_FILE, CONTENTS_DIR), Exception(
                "Failed to unzip contents"
            )
            logger.info("Contents downloaded and unzipped")
            return CONTENTS_DIR
        except:
            print_exc()
            continue

    return CONTENTS_DIR


async def xml_to_json(input_path, output_path, callback=None, overwrite=False):
    if not output_path:
        output_path = input_path.parent / f"{input_path.stem}.json"
    if output_path.is_file() and not overwrite:
        return output_path
    with open(input_path, "r", encoding="utf-8") as input_file:
        xml = input_file.read()
        d = xmltodict.parse(xml)
        with open(output_path, "w", encoding="utf-8") as output_file:
            json.dump(
                d,
                output_file,
                ensure_ascii=False,
            )
    if callback:
        callback()


async def xml_dir_walker(dir: Path, suffix_filter=[".xml"]):
    for file in dir.iterdir():
        if file.is_file():
            if file.suffix in suffix_filter:
                yield file
            else:
                logger.debug(f"Skipping {file}")
        elif file.is_dir():
            async for r_file in xml_dir_walker(
                file,
                suffix_filter=suffix_filter,
            ):
                yield r_file


async def main():
    contents_dir = await init_contents(ROOT / "data")
    JSON_DOCUMENTS_DIR = ROOT / "data" / "json_documents"
    JSON_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    xml_file_list = [file async for file in xml_dir_walker(contents_dir)]

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

        task_id = __FILE_PROGRESS__.add_task(
            "convert",
            total=len(xml_file_list),
        )
        task_list = []
        for file in xml_file_list:
            task_list.append(
                asyncio.create_task(
                    xml_to_json(
                        file,
                        JSON_DOCUMENTS_DIR / f"{file.stem}.json",
                        partial(__FILE_PROGRESS__.update, task_id, advance=1),
                    ),
                )
            )

        await asyncio.gather(*task_list)

        __FILE_PROGRESS__.stop_task(task_id)

        logger.info(f"Converted {len(xml_file_list)} xml files to json")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
