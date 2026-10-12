import requests
import csv
import time
import random
import re

COOKIE = "hiijack=0; supportWebp=true; abPolicies=%7B%22g17%22%3A0%2C%22g16%22%3A0%2C%22g18%22%3A1%2C%22g19%22%3A0%2C%22g14%22%3A0%7D; supportwebp=true; newstatisticUUID=1791774872_697166665; fu=373437429; _csrfToken=7dea70d6-d522-451c-9cda-cf6e73fb961c; traffic_utm_referer=; Hm_lvt_f00f67093ce2f38f215010b699629083=1791774872; Hm_lpvt_f00f67093ce2f38f215010b699629083=1791774872; HMACCOUNT=687FD36B28E3F3B3; traffic_search_engine=; se_ref=; Hm_lvt_1d7d9ab48732e057a5e22e962e5797a6=1791775035; hiijack=0; Hm_lpvt_1d7d9ab48732e057a5e22e962e5797a6=1791775291"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Edg/155.0.0.0 Mobile Safari/537.36",
    "Cookie": COOKIE,
    "Referer": "https://m.qidian.com/rank/readindex/",
    "Accept": "application/json, text/plain, */*"
}

def crawl_one_page(page_num):
    # 从Cookie中自动提取csrfToken，避免手动复制出错
    csrf_match = re.search(r"_csrfToken=([^;]+)", COOKIE)
    csrf_token = csrf_match.group(1) if csrf_match else ""

    # 修正：分页参数名必须是 pageNum
    url = (
        f"https://m.qidian.com/webcommon/rank/readIndexlist"
        f"?gender=male"
        f"&pageNum={page_num}"          # ← 关键修正：加上参数名 pageNum
        f"&catId=-1"
        f"&_csrfToken={csrf_token}"
    )

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        res_data = response.json()
    except Exception as e:
        print(f"第{page_num}页请求失败：{e}")
        return []

    # 从接口结构提取小说列表
    book_list = res_data.get("data", {}).get("records", [])
    if not book_list:
        print(f"第{page_num}页无小说数据")
        return []

    page_data = []
    for book in book_list:
        try:
            rank = book.get("rankNum", 0)
            book_name = book.get("bName", "未知")
            author = book.get("bAuth", "未知")
            category = book.get("cat", "未知")
            sub_category = book.get("subCat", "")
            word_count = book.get("cnt", "未知")
            intro = book.get("desc", "无简介")

            page_data.append([rank, book_name, author, category, sub_category, word_count, intro])
        except Exception as e:
            print(f"单条解析失败：{e}")
            continue

    print(f"第{page_num}页爬取完成，获取{len(page_data)}本小说")
    return page_data

def save_to_csv(data, filename="qidian_readindex_books.csv"):
    headers = ["排名", "小说名称", "作者", "分类", "子类", "字数", "简介"]
    with open(filename, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
    print(f"数据已保存到 {filename}")

def main():
    all_data = []
    # 共510本，每页20条，爬前3页做演示（可按需改成 range(1, 26) 爬完整榜单）
    for page in range(1, 4):
        page_data = crawl_one_page(page)
        all_data.extend(page_data)
        time.sleep(random.uniform(2, 3))

    save_to_csv(all_data)
    print(f"全部爬取完成，共获取{len(all_data)}条数据")

if __name__ == "__main__":
    main()
