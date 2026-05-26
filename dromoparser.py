import re
import asyncio
import random
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

list_of_cars = []
data = []

cities = ["moscow", "spb", "ryazan", "habarovsk", "vladivostok"]

car_models = [
    ("subaru", "impreza"),
    ("kia", "stinger"),
    ("kia", "rio"),
    ("skoda", "octavia"),
    ("toyota", "crown"),
    ("porsche", "panamera"),
    ("cadillac", "escalade"),
]


async def close_popups(page):
    try:
        for _ in range(3):
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(400)
    except:
        pass


async def check_for_captcha(page):
    try:
        html = await page.content()
        text_lower = html.lower()
        if any(word in text_lower for word in ["я не робот", "капча", "cloudflare", "подтвердите"]):
            print(" КАПЧА!")
            await page.pause()
            return True
        return False
    except:
        return False


async def parse_drom_card(url, context_page=None):
    
    if context_page:
        page = context_page
        await page.goto(url, wait_until="domcontentloaded")
    else:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")

    await check_for_captcha(page)

    html = await page.content()
    soup = BeautifulSoup(html, "html.parser")

    if not context_page:
        await browser.close()


    price = None
    price_tag = soup.find('div', {'data-ftid': 'bulletin-price'})
    if price_tag:
        raw = price_tag.get_text(strip=True)
        digits = re.sub(r'\D', '', raw)
        if digits:
            price = int(digits)

    if not price:
        price_match = re.search(r'(\d[\d\snbsp;]*)\s*₽', html, re.I)
        if price_match:
            digits = re.sub(r'\D', '', price_match.group(1))
            if digits:
                price = int(digits)



    mileage = None

    mileage_row = soup.find('tr', {'data-ftid': 'specification-mileage'})
    if mileage_row:
        value_td = mileage_row.find('td', {'data-ftid': 'value'})
        if value_td:
            raw_mileage = value_td.get_text(strip=True)
            digits = re.sub(r'\D', '', raw_mileage)
            if digits:
                mileage = int(digits)


    if not mileage:
        mileage_match = re.search(r'(\d[\d\s]*)\s*км', html)
        if mileage_match:
            mileage = int("".join(filter(str.isdigit, mileage_match.group(1))))


    publish_date = None
    date_match = re.search(r'Объявление.*?от\s*(\d{1,2}\.\d{1,2}\.\d{4})', html, re.I)
    if date_match:
        publish_date = date_match.group(1)
    else:
        date_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', html)
        if date_match:
            publish_date = date_match.group(1)

    return {
        "price": price, 
        "publish_date": publish_date, 
        "mileage": mileage
    }


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=20)
        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"})

        for city in cities:
            for firm, model in car_models:
                url = f"https://auto.drom.ru/{city}/{firm}/{model}/used/"
                print(f"Парсим: {firm.upper()} {model.upper()} — {city.upper()}")

                await page.goto(url, wait_until="domcontentloaded")

                await close_popups(page)

                for _ in range(6):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")


                html = await page.content()
                link_pattern = re.compile(r'href="(https?://auto\.drom\.ru/[^"]+?\.html)"')
                all_links = link_pattern.findall(html)

                unique_links = []
                base_pattern = f"/{city}/{firm}/{model}/"
                for link in all_links:
                    if link not in unique_links and base_pattern in link:
                        unique_links.append(link)

                print(f"Найдено уникальных объявлений: {len(unique_links)}")

                if not unique_links:
                    print("Ссылки не найдены.")
                    continue

                for i, full_link in enumerate(unique_links[:7]):
                    try:
                        print(f"\n")
                        print(f"Объявление №{i+1}")

                        card_data = await parse_drom_card(full_link, context_page=page)

                        title = full_link.split('/')[-2].replace('-', ' ').title()
                        price_text = f"{card_data['price']} ₽" if card_data['price'] else "Не найдено"
                        mileage_text = f"{card_data['mileage']} км" if card_data['mileage'] else "Не найдено"

                        print("Название:", title)
                        print("Цена:", price_text)
                        print("Дата:", card_data["publish_date"])
                        print("Пробег:", mileage_text)
                        print("Ссылка:", full_link)

                        data.append({
                            "Название": title,
                            "Цена": price_text,
                            "Город": city,
                            "Дата публикации": card_data["publish_date"],
                            "Пробег": mileage_text,
                            "Ссылка": full_link
                        })

                    except Exception as e:
                        print(f"{e}")

        await browser.close()

    
    if data:
        df = pd.DataFrame(data)
        df = df[["Название", "Цена", "Город", "Дата публикации", "Пробег", "Ссылка"]]
        print("\n" + "="*100)
        print(df)

        OUTPUT_EXCEL = "drom_tachki1.xlsx"
        df.to_excel(OUTPUT_EXCEL, index=False)
        print(f" Файл сохранён: {OUTPUT_EXCEL}")
    else:
        print(" Ошибка с таблицей")


if __name__ == "__main__":
    asyncio.run(main())