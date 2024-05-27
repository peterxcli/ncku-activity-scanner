import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from colorlog import ColoredFormatter


def setup_logger():
    """Setup the colored logger."""
    logger = logging.getLogger("ActivityLogger")
    handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s%(reset)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def fetch_and_check_activity(base_url: str, act_id: int, logger: logging.Logger):
    if act_id % 500 == 0:
        logger.warning(f"Checking activity ID {act_id}...")
    url = f"{base_url}?c=apply&m=ajax_query&act_id={act_id}"
    try:
        response = requests.get(url, timeout=10)
        if "error-no active data" in response.text:
            return None
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", class_="grid_data")
        if table:
            rows = table.find_all("tr")
            register_start, register_end = None, None
            meals_provided = False
            activity_data = {}
            for row in rows:
                cells = row.find_all("th")
                data_cells = row.find_all("td")
                for idx, cell in enumerate(cells):
                    if "報名開始" in cell.text:
                        register_start = datetime.strptime(
                            data_cells[idx].text.strip(), "%Y/%m/%d %H:%M"
                        )
                    elif "報名結束" in cell.text:
                        register_end = datetime.strptime(
                            data_cells[idx].text.strip(), "%Y/%m/%d %H:%M"
                        )
                    elif (
                        "是否提供餐點" in cell.text
                        and "是" in data_cells[idx].text.strip()
                    ):
                        meals_provided = True
                    activity_data[cell.text.strip()] = data_cells[idx].text.strip() if idx < len(data_cells) else ""
            if meals_provided and register_start and register_end:
                now = datetime.now()
                days_till_start = (register_start - now).days
                if register_start <= now <= register_end or 0 <= days_till_start <= 7:
                    required_fields = ["活動分享網址", "活動名稱", "活動地點", "活動開始", "活動結束", "報名開始", "報名結束", "是否提供餐點"]
                    result_data = [activity_data.get(field, " ") for field in required_fields]
                    name_with_link = f"[{activity_data.get('活動名稱', 'No Name Available')}](https://activity.ncku.edu.tw/index.php?c=apply&no={act_id})"
                    result_data[1] = name_with_link  # Replace name with link
                    result_data = result_data[1:]
                    return result_data
    except requests.RequestException as e:
        logger.error(f"Activity ID {act_id}: Failed to fetch data due to {e}")
    return None



def handle_shutdown(executor: ThreadPoolExecutor, logger: logging.Logger):
    logger.warning("Shutting down executor...")
    executor.shutdown(wait=True, cancel_futures=True)
    logger.warning("Shutdown complete.")


def main():
    logger = setup_logger()
    base_url = "https://activity.ncku.edu.tw/index.php"
    start_id = 14000
    end_id = 14800
    executor = ThreadPoolExecutor(max_workers=10)
    futures = {executor.submit(fetch_and_check_activity, base_url, act_id, logger): act_id for act_id in range(start_id, end_id + 1)}

    results = []
    try:
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    finally:
        handle_shutdown(executor, logger)
        if results:
            headers = ["Activity", "Location", "Start", "End", "Registration Start", "Registration End", "Meals Provided"]
            table = "| " + " | ".join(headers) + " |\n"
            table += "| --- " * len(headers) + "|\n"
            for res in results:
                table += "| " + " | ".join(res) + " |\n"
            print(table)

if __name__ == "__main__":
    main()
