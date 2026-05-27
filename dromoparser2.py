import re
import asyncio
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


class DromParser:
    def __init__(self):
        self.data = []
        self.cities = ["moscow", "spb", "ryazan", "habarovsk", "vladivostok"]
        self.car_models = [
            ("subaru", "impreza"),
            ("kia", "stinger"),
            ("kia", "rio"),
            ("skoda", "octavia"),
            ("toyota", "crown"),
            ("porsche", "panamera"),
            ("cadillac", "escalade"),
        ]

    async def close_popups(self, page):
        try:
            for _ in range(3):
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(400)
        except:
            pass

    async def check_for_captcha(self, page):
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

    async def parse_drom_card(self, url, context_page=None):
        if context_page:
            page = context_page
            await page.goto(url, wait_until="domcontentloaded")
        else:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded")

        await self.check_for_captcha(page)

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        if not context_page:
            await browser.close()

        # Цена
        price = None
        price_tag = soup.find('div', {'data-ftid': 'bulletin-price'})
        if price_tag:
            digits = re.sub(r'\D', '', price_tag.get_text(strip=True))
            if digits:
                price = int(digits)

        if not price:
            price_match = re.search(r'(\d[\d\s]*)\s*₽', html)
            if price_match:
                price = int(re.sub(r'\D', '', price_match.group(1)))

        # Пробег
        mileage = None
        mileage_row = soup.find('tr', {'data-ftid': 'specification-mileage'})
        if mileage_row:
            value_td = mileage_row.find('td', {'data-ftid': 'value'})
            if value_td:
                digits = re.sub(r'\D', '', value_td.get_text(strip=True))
                if digits:
                    mileage = int(digits)

        if not mileage:
            mileage_match = re.search(r'(\d[\d\s]*)\s*км', html)
            if mileage_match:
                mileage = int(re.sub(r'\D', '', mileage_match.group(1)))

        # Дата публикации
        publish_date = None
        date_match = re.search(r'Объявление.*?от\s*(\d{1,2}\.\d{1,2}\.\d{4})', html, re.I)
        if date_match:
            publish_date = date_match.group(1)

        # Просмотры
        views = None
        views_match = re.search(
            r'xmlns="http://www\.w3\.org/2000/svg"[^>]*>.*?</svg>\s*<!--\s*-->\s*(\d+)',
            html, 
            re.DOTALL
        )
        if views_match:
            views = int(views_match.group(1))

        if not views:
            views_match = re.search(r'<svg[^>]*>.*?</svg>.*?(\d{1,6})', html, re.DOTALL | re.I)
            if views_match:
                views = int(views_match.group(1))

        if not views:
            views_match = re.search(r'(\d{1,6})\s*(?:просмотр|просмотра|просмотров)', html)
            if views_match:
                views = int(views_match.group(1))

        return {
            "price": price,
            "publish_date": publish_date,
            "mileage": mileage,
            "views": views
        }

    async def main(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=20)
            page = await browser.new_page()

            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

            for city in self.cities:
                for firm, model in self.car_models:
                    url = f"https://auto.drom.ru/{city}/{firm}/{model}/used/"
                    print(f"Парсим: {firm.upper()} {model.upper()} — {city.upper()}")

                    await page.goto(url, wait_until="domcontentloaded")
                    await self.close_popups(page)

                    for _ in range(6):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                    html = await page.content()

                    # Количество объявлений
                    total_announcements = None
                    total_match = re.search(r'(\d[\d\s]*)\s*(?:объявлен(?:ие|ия|ий))', html)
                    if total_match:
                        total_announcements = int(re.sub(r'\D', '', total_match.group(1)))

                    # Ссылки
                    link_pattern = re.compile(r'href="(https?://auto\.drom\.ru/[^"]+?\.html)"')
                    all_links = link_pattern.findall(html)

                    unique_links = []
                    base_pattern = f"/{city}/{firm}/{model}/"
                    for link in all_links:
                        if link not in unique_links and base_pattern in link:
                            unique_links.append(link)

                    print(f"Найдено уникальных объявлений: {len(unique_links)} | Всего: {total_announcements or 'Не найдено'}")

                    if not unique_links:
                        continue

                    for i, full_link in enumerate(unique_links[:7]):
                        try:
                            print(f"\nОбъявление №{i+1}")

                            card_data = await self.parse_drom_card(full_link, context_page=page)

                            title = full_link.split('/')[-2].replace('-', ' ').title()
                            price_text = f"{card_data['price']} ₽" if card_data['price'] else "Не найдено"
                            mileage_text = f"{card_data['mileage']} км" if card_data['mileage'] else "Не найдено"
                            views_text = f"{card_data['views']} просмотров" if card_data['views'] is not None else "Не найдено"

                            print("Название:", title)
                            print("Цена:", price_text)
                            print("Дата:", card_data["publish_date"])
                            print("Пробег:", mileage_text)
                            print("Просмотры:", views_text)
                            print("Ссылка:", full_link)

                            self.data.append({
                                "Название": title,
                                "Цена": price_text,
                                "Город": city,
                                "Дата публикации": card_data["publish_date"],
                                "Пробег": mileage_text,
                                "Просмотры": views_text,
                                "Количество_объявлений": total_announcements,
                                "Ссылка": full_link
                            })

                        except Exception as e:
                            print(f"Ошибка: {e}")

            await browser.close()

            # Сохранение в Excel
            if self.data:
                df = pd.DataFrame(self.data)
                df = df[["Название", "Цена", "Город", "Дата публикации", "Пробег",
                         "Просмотры", "Количество_объявлений", "Ссылка"]]
                print("\n" + "="*120)
                print(df)

                OUTPUT_EXCEL = "drom_tachki1.xlsx"
                df.to_excel(OUTPUT_EXCEL, index=False)
                print(f"\nФайл сохранён: {OUTPUT_EXCEL}")
            else:
                print("Нет данных для сохранения")


if __name__ == "__main__":
    parser = DromParser()
    asyncio.run(parser.main())