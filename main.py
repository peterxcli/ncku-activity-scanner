from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def fetch_and_check_activity(base_url, act_id):
    url = f"{base_url}?c=apply&m=ajax_query&act_id={act_id}"
    try:
        response = requests.get(url, timeout=10)
        if "error-no active data" in response.text:
            return
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", class_="grid_data")
        if table:
            rows = table.find_all("tr")
            register_start, register_end = None, None
            meals_provided = False
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

            if meals_provided and register_start and register_end:
                now = datetime.now()
                days_till_start = (register_start - now).days
                if register_start <= now <= register_end or 0 <= days_till_start <= 7:
                    return f"Activity ID {act_id}, Meals provided, URL: {url}, Register from {register_start} to {register_end}"
    except requests.RequestException as e:
        return f"Activity ID {act_id}: Failed to fetch data due to {e}"
    return None


def main():
    base_url = "https://activity.ncku.edu.tw/index.php"
    start_id = 14000
    end_id = 20000
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_and_check_activity, base_url, act_id): act_id
            for act_id in range(start_id, end_id + 1)
        }
        for future in futures:
            result = future.result()
            if result:
                print(result)


if __name__ == "__main__":
    main()
