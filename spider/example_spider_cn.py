from pathlib import Path
import httpx
from multiprocessing.pool import ThreadPool
import json
import pandas as pd
from loguru import logger
from traceback import print_exc
from itertools import repeat
from tqdm import tqdm

__CHUNK_SIZE__ = 1024 * 64

search_url = "https://rmfyalk.court.gov.cn/cpws_al_api/api/cpwsAl/search"
download_url = "https://rmfyalk.court.gov.cn/cpws_al_api/api/cpwsAl/contentDownload?id="

# COOKIES = httpx.Cookies()


def downloader(args):
    client, data, dir = args
    try:
        id = data["id"]
        url = download_url + id
        file_path = dir / f"{id}.pdf"
        tmp_path = dir / f"{id}.pdf.tmp"
        if file_path.is_file():
            return file_path
        if tmp_path.is_file():
            tmp_path.unlink()

        with client.stream(
            "GET",
            url,
        ) as resp:
            with open(
                tmp_path,
                "wb",
            ) as f:
                for chunk in resp.iter_bytes(__CHUNK_SIZE__):
                    f.write(chunk)
                f.flush()

            tmp_path.rename(file_path)
        return file_path
    except Exception as e:
        print_exc()
        return e


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent
    example_dir = ROOT / "examples_cn"
    config_json = example_dir / f"{Path(__file__).stem}.json"
    index_json = example_dir / f"{Path(__file__).stem}_index.json"
    csv = example_dir / f"{Path(__file__).stem}_index.csv"
    doc_dir = example_dir / "documents"

    example_dir.mkdir(parents=True, exist_ok=True)
    doc_dir.mkdir(parents=True, exist_ok=True)

    CONFIG = {}
    with open(config_json, "r") as f:
        CONFIG = json.load(f)

    # for k, v in CONFIG["cookies"].items():
    #     COOKIES.set(
    #         k,
    #         v,
    #         "rmfyalk.court.gov.cn",
    #     )

    with httpx.Client(headers=CONFIG["headers"]) as client:
        index_data = {}
        if index_json.is_file():
            with open(index_json, "r", encoding="utf8") as f:
                index_data = json.load(f)
        else:
            total_pages = 1
            page = 1
            while page <= total_pages:
                resp = client.post(
                    search_url,
                    json={
                        "page": page,
                        "size": 50,
                        "lib": "qb",
                        "searchParams": {
                            "userSearchType": 1,
                            "isAdvSearch": "0",
                            "selectValue": "qw",
                            "lib": "cpwsAl_qb",
                            "sort_field": "",
                        },
                    },
                )
                if total_pages == 1:
                    total = resp.json()["data"]["totalCount"]
                    total_pages = (total + 50) // 50
                if not index_data:
                    index_data = resp.json()
                else:
                    index_data["data"]["datas"].extend(resp.json()["data"]["datas"])
                logger.info(f"Page {page} of {total_pages} downloaded")
                page += 1
            print(f"Index downloaded with msg {index_data['msg']}")
            with open(index_json, "w", encoding="utf8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=4)

        # transform to csv
        df = pd.DataFrame(index_data["data"]["datas"])
        df.to_csv(csv)

        pool = ThreadPool(CONFIG["threads"])

        results = pool.imap(
            downloader,
            zip(
                repeat(client),
                index_data["data"]["datas"],
                repeat(doc_dir),
            ),
        )
        loop = tqdm(
            results, total=len(index_data["data"]["datas"]), desc="Downloading..."
        )
        status_dict = {"success": 0, "failed": 0, "last_error": ""}
        for result in loop:
            if isinstance(result, Path):
                status_dict["success"] += 1
            else:
                status_dict["failed"] += 1
                status_dict["last_error"] = str(result)
            loop.set_postfix(status_dict)

        if status_dict["failed"]:
            exit(1)
        else:
            exit(0)
