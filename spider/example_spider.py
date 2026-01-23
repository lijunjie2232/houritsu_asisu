from threading import Thread
from wsgiref import headers
import httpx
import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
from pathlib import Path
from tqdm import tqdm
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
from urllib.parse import urlparse, parse_qs
from itertools import repeat
from traceback import print_exc
from time import sleep

__THREAD_NUM__ = 7

__DOWNLOAD_URL__ = "https://legaldoc.jp/res/hanrei/%s"

__CHUNK_SIZE__ = 1024 * 64


def parse_multiple_entries_xml(xml_content):
    # Parse the XML content
    root = ET.fromstring(xml_content)

    # Find all entry tags that contain partial-response
    entries = root.findall(".//entry")

    all_data_list = []

    pool = Pool(__THREAD_NUM__)

    results = pool.imap(_parse_multiple_entries_xml, entries)

    for result in tqdm(results, desc="Parsing entries", total=len(entries)):
        all_data_list.extend(result)

    # Create DataFrame
    df = pd.DataFrame(all_data_list)

    return df


def _parse_multiple_entries_xml(entry):
    """
    Parse multiple entry tags in the XML and extract information into a pandas DataFrame

    Args:
        xml_content (str): The XML content as string

    Returns:
        pd.DataFrame: DataFrame containing extracted court case information from all entries
    """

    # Get the start attribute for this entry
    start_value = entry.get("start", "0")

    # Find the CDATA section which contains HTML table within this entry
    update_element = entry.find('.//update[@id="j_idt209-courtsDataTable"]')

    records = []

    if update_element is not None:
        cdata_section = update_element.text
        soup = BeautifulSoup(cdata_section, "html.parser")

        # Extract data from the table
        rows = soup.find_all("tr")[1:]  # Skip header row

        for row in rows:
            cells = row.find_all(["td"])

            if len(cells) >= 4:  # Ensure we have enough cells
                # Extract court type badge
                court_type_badge = (
                    cells[0].find("span", class_="badge") if cells[0] else None
                )
                court_type_class = (
                    court_type_badge.get("class")[2] if court_type_badge else ""
                )

                # Extract case details from second cell
                case_link = cells[1].find("a", class_="link-pdf") if cells[1] else None
                case_title = case_link.text.strip() if case_link else ""

                # Extract court info
                items_divs = cells[1].find_all("div", class_="items")
                court_info = {}
                if items_divs:
                    for item_div in items_divs:
                        divs = item_div.find_all("div")
                        for div in divs:
                            text = div.get_text()
                            if "裁判所" in text:  # Court
                                court_info["court"] = (
                                    text.split("：")[1].strip() if "：" in text else ""
                                )
                            elif "裁判日" in text:  # Judgment date
                                court_info["judgment_date"] = (
                                    text.split("：")[1].strip() if "：" in text else ""
                                )

                # Extract case number from third cell
                case_number = cells[2].get_text(strip=True) if cells[2] else ""

                # Extract additional info from fourth cell (visible on small screens)
                case_outline = cells[3]
                event_number_alt = ""
                if case_outline:
                    for div in case_outline.find_all("div"):
                        text = div.get_text()
                        if "事件番号" in text and "：" in text:
                            event_number_alt = text.split("：")[1].strip()

                # Use case number from third cell primarily, fallback to one from fourth cell
                final_case_number = case_number or event_number_alt

                # Create a record dictionary
                record = {
                    "start_index": start_value,  # Track which entry this came from
                    "case_title": case_title,
                    "court_type": court_type_class,
                    "court_name": court_info.get("court", ""),
                    "judgment_date": court_info.get("judgment_date", ""),
                    "case_number": final_case_number,
                    "detail_url": case_link.get("href") if case_link else "",
                    "pdf_url": (
                        cells[1].find("a", class_="link-pdf").get("href")
                        if cells[1] and cells[1].find("a", class_="link-pdf")
                        else ""
                    ),
                }
                records.append(record)

    return records


def parse_court_cases_xml(xml_content):
    """
    Original function for compatibility - processes single entry
    This maintains backward compatibility with your existing code
    """
    return parse_multiple_entries_xml(xml_content)


def read_court_cases_file(file_path):
    """
    Read the XML file and return DataFrame

    Args:
        file_path (str): Path to the XML file

    Returns:
        pd.DataFrame: DataFrame containing extracted court case information
    """
    with open(file_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    return parse_multiple_entries_xml(xml_content)


def parse_court_cases_from_entries(file_path_or_content, is_file=True):
    """
    Flexible function to parse court cases either from file path or directly from content

    Args:
        file_path_or_content: Either file path (string) or XML content (string)
        is_file: True if first parameter is a file path, False if it's XML content

    Returns:
        pd.DataFrame: DataFrame containing extracted court case information from all entries
    """
    if is_file:
        with open(file_path_or_content, "r", encoding="utf-8") as f:
            xml_content = f.read()
    else:
        xml_content = file_path_or_content

    return parse_multiple_entries_xml(xml_content)


def extract_filename_from_url(url):
    """
    Extract filename from URL query parameters
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Get the 'f' parameter which contains the filename
    filename_list = query_params.get("f", [])

    if filename_list:
        return filename_list[0]  # Return the first occurrence
    return None


def downloader(args):
    client, filename, dir = args
    try:
        url = __DOWNLOAD_URL__ % filename
        file_path = dir / filename
        tmp_path = dir / f"{filename}.tmp"
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
        sleep(1)
        return file_path
    except Exception as e:
        # print_exc()
        return e


# Example usage:
if __name__ == "__main__":
    # Process all entries in the XML file
    ROOT = Path(__file__).resolve().parent
    examples_dir = ROOT / "examples"
    document_dir = examples_dir / "documents"
    xml_file = examples_dir / "legal_export_n3356_1768705367915.xml"
    csv_file = examples_dir / "legal_export_n3356_1768705367915.csv"

    examples_dir.mkdir(parents=True, exist_ok=True)
    document_dir.mkdir(parents=True, exist_ok=True)

    df = None
    if not csv_file.is_file():
        df = read_court_cases_file(xml_file)
        df["file_name"] = df["pdf_url"].apply(extract_filename_from_url)
        # Save to CSV
        df.to_csv(csv_file, index=False)
    else:
        df = pd.read_csv(csv_file)

    with httpx.Client(
        headers={
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
        },
        proxy="socks5://127.0.0.1:7890",
    ) as client:
        pool = ThreadPool(__THREAD_NUM__)

        results = pool.imap(
            downloader,
            zip(
                repeat(client),
                df["file_name"].tolist(),
                repeat(document_dir),
            ),
        )

        loop = tqdm(results, desc="Downloading...", total=len(df))
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
