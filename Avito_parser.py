import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import random


class Program:
    def __init__(self):
        self.list_of_cars = []
        self.data = []
        self.cities = ["ryazan", "moskva", "sankt-peterburg", "habarovsk", "vladivostok"]
        self.car_models = [
            ("subaru", "impreza"),
            ("kia", "stinger"),
            ("kia", "rio"),
            ("skoda", "octavia"),
            ("toyota", "crown"),
            ("porsche", "panamera"),
            ("cadillac", "escalade"),
        ]

    async def check_for_captcha(self, page):
        try:
            html = await page.content()
            text_lower = html.lower()
            current_url = page.url.lower()

            captcha_indicators = [
                "attention required", "please verify you are a human",
                "я не робот", "подтвердите, что вы не робот",
                "ddos-guard", "just a moment", "Отключить VPN.", "для решения капчи"
            ]

            for indicator in captcha_indicators:
                if indicator in text_lower:
                    print(f"Капча по тексту на странице! ({indicator})")
                    print("Решите капчу вручную в браузере.")
                    await page.pause()
                    await page.wait_for_timeout(1000)
                    return True

            if any(x in current_url for x in ["challenge", "captcha", "verify"]):
                print("КАПЧА по URL!")
                await page.pause()
                await page.wait_for_timeout(1000)
                return True

            captcha_elements = await page.locator('iframe[src*="captcha"], iframe[src*="challenge"]').count()
            if captcha_elements > 0:
                print("iframe-капча!")
                await page.pause()
                await page.wait_for_timeout(1000)
                return True

            return False

        except Exception as e:
            print(f"Ошибка при проверке капчи: {e}")
            return False

    async def parse_avito_card(self, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            })

            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(1000, 1500))
            await self.check_for_captcha(page)
            html = await page.content()

            await browser.close()

        soup = BeautifulSoup(html, "html.parser")

        price = None
        price_tag = soup.find(attrs={"data-marker": "item-view/item-price"})
        if price_tag:
            raw_price = price_tag.get_text(strip=True)
            price = int("".join(filter(str.isdigit, raw_price)))

        publish_date = None
        date_tag = soup.find("span", attrs={"data-marker": "item-view/item-date"})
        if date_tag:
            publish_date = date_tag.get_text(strip=True)

        mileage = None
        text = soup.get_text(" ", strip=True)
        mileage_match = re.search(r"(\d[\d\s]*)\s?км", text)
        if mileage_match:
            mileage = int("".join(filter(str.isdigit, mileage_match.group(1))))

        views = None
        views_tag = soup.find(attrs={"data-marker": "item-view/total-views"})
        if views_tag:
            views_text = views_tag.get_text(strip=True)
            views_match = re.search(r"(\d[\d\s]*)", views_text)
            if views_match:
                views = int("".join(filter(str.isdigit, views_match.group(1))))

        return {
            "price": price,
            "publish_date": publish_date,
            "mileage": mileage,
            "views": views
        }

    async def main(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=100)
            page = await browser.new_page()

            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            })

            for cit in self.cities:
                for firm, model in self.car_models:
                    url1 = f"https://www.avito.ru/{cit}/avtomobili/{firm}/{model}"
                    print(f"\n🔍 Парсим: {cit} — {firm} {model}")

                    await page.goto(url1, wait_until="domcontentloaded")
                    await page.wait_for_timeout(500)

                    for _ in range(5):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(200)

                    total_ads = None
                    try:
                        count_elem = await page.locator('[data-marker="page-title/count"]').first.inner_text(timeout=1000)
                        total_ads_match = re.search(r"(\d[\d\s]*)", count_elem)
                        if total_ads_match:
                            total_ads = int("".join(filter(str.isdigit, total_ads_match.group(1))))
                            print(f"Всего объявлений: {total_ads}")
                    except:
                        print("Не удалось получить количество объявлений")

                    cards = await page.locator('div[data-marker="item"]').all()
                    print(f"Найдено карточек: {len(cards)}")

                    for i, card in enumerate(cards[:8]):
                        try:
                            print(f"Объявление №{i+1} | {cit} | {firm} {model}")

                            title = await card.locator('[data-marker="item-title"]').first.inner_text(timeout=1000)
                            price_elem = await card.locator('[data-marker="item-price"]').first.inner_text(timeout=1000)
                            link_elem = card.locator('a[data-marker="item-title"]').first
                            relative_link = await link_elem.get_attribute("href")

                            full_link = "https://www.avito.ru" + relative_link if relative_link else None

                            if full_link:
                                self.list_of_cars.append(full_link)

                            spisok = await self.parse_avito_card(full_link)

                            self.data.append({
                                "Название": title.strip(),
                                "Цена": price_elem.strip(),
                                "Город": cit,
                                "Дата публикации": spisok["publish_date"],
                                "Пробег": spisok["mileage"],
                                "Просмотры": spisok["views"],
                                "Всего объявлений модели": total_ads,
                                "Ссылка": full_link
                            })

                        except Exception as e:
                            print(f"{e}")
                            await self.check_for_captcha(page)

            await browser.close()

    def run(self):
        asyncio.run(self.main())

        if not self.data:
            print("Нет данных для сохранения.")
            return

        df = pd.DataFrame(self.data)
        df = df[[
            "Название", "Цена", "Город", "Дата публикации", "Пробег",
            "Просмотры", "Всего объявлений модели", "Ссылка"
        ]]

        print("\n" + "="*80)
        print(df.head())
        print(f"Всего собрано объявлений: {len(df)}")

        OUTPUT_EXCEL = "vse_tachki_mira.xlsx"
        df.to_excel(OUTPUT_EXCEL, index=False)
        print(f"Файл успешно сохранён: {OUTPUT_EXCEL}")


if __name__ == "__main__":
    program = Program()
    program.run()