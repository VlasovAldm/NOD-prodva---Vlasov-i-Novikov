# тут сейчас будем объединять в ништяк настоящий
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio

import asyncio
from playwright.async_api import async_playwright
import pandas as pd

import random

list_of_cars=[]
data= []

cities = ["ryazan","moskva","sankt-peterburg","habarovsk","vladivostok"]
firm = "subaru"
model = "impreza"


car_models = [
    ("subaru","impreza"),
    ("kia","stinger"),
    ("kia","rio"),
    ("skoda","octavia"),
    ("toyota","crown"),
    ("porsche","panamera"),
    ("cadillac","escalade"),
]



async def check_for_captcha(page):
    """Проверяет наличие капчи. Возвращает True, если капча обнаружена."""
    try:
        html = await page.content()
        text_lower = html.lower()
        current_url = page.url.lower()

        # Более точные индикаторы капчи
        captcha_indicators = [ 
            "attention required", 
            "please verify you are a human",
            "я не робот",
            "подтвердите, что вы не робот",
            "ddos-guard", 
            "just a moment",
            "Отключить VPN.",
            "для решения капчи"

        ]

        # Проверяем по тексту
        for indicator in captcha_indicators:
            if indicator in text_lower:
                print(f"\n🚨 КАПЧА ОБНАРУЖЕНА! ({indicator})")
                print("Решите капчу вручную в браузере.")
                print("После решения нажмите кнопку **Resume** в Playwright Inspector.\n")
                
                await page.pause()
                await page.wait_for_timeout(1500)  # пауза после продолжения
                return True

        # Проверка по URL (Cloudflare и подобные)
        if any(x in current_url for x in ["challenge", "captcha", "verify"]):
            print("\n🚨 КАПЧА по URL!")
            await page.pause()
            await page.wait_for_timeout(1500)
            return True

        # Дополнительная проверка — наличие формы капчи
        captcha_elements = await page.locator('iframe[src*="captcha"], iframe[src*="challenge"]').count()
        if captcha_elements > 0:
            print("\n🚨 Обнаружена iframe-капча!")
            await page.pause()
            await page.wait_for_timeout(1500)
            return True

        return False  # ← Капчи нет — продолжаем нормально

    except Exception as e:
        print(f"Ошибка при проверке капчи: {e}")
        return False



async def parse_avito_card(url, context_page=None):
    """Парсим одну карточку. Если передали context_page — используем его, иначе создаём новый"""
    if context_page:  
        # Используем уже открытый браузер из main()
        page = context_page
        await page.goto(url, wait_until="domcontentloaded")
    else:
        # Запасной вариант — отдельный браузер
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")

    await page.wait_for_timeout(random.randint(2500, 3000))
    
    await check_for_captcha(page)   # ← проверка капчи
    
    html = await page.content()
    
    # Если создавали отдельный браузер — закрываем
    if not context_page:
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")

    # ... весь твой код парсинга цены, даты, пробега остаётся без изменений ...
    
    # (оставь как есть)

    # =========================
    # ЦЕНА
    # =========================

    price = None
    
    price_tag = soup.find(
        attrs={"data-marker": "item-view/item-price"}
    )
    if not price_tag: 
        # решение капчи
        page.pause()
        page.click("#submit-button")
    
    if price_tag:

        raw_price = price_tag.get_text(strip=True)

        price = int(
            "".join(filter(str.isdigit, raw_price))
        )



    # =========================
    # ДАТА
    # =========================

    publish_date = None

    date_tag = soup.find(
        "span",
        attrs={"data-marker": "item-view/item-date"}
    )

    if date_tag:
        publish_date = date_tag.get_text(strip=True)

    # =========================
    # ПРОБЕГ
    # =========================

    mileage = None

    text = soup.get_text(" ", strip=True)

    mileage_match = re.search(
        r"(\d[\d\s]*)\s?км",
        text
    )

    if mileage_match:
        mileage = int(
            "".join(filter(str.isdigit,
            mileage_match.group(1)))
        )

    return {
        "price": price,
        "publish_date": publish_date,
        "mileage": mileage
    }




async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=600)
        page = await browser.new_page()
        

        
        for cit in cities:
            for firm,model in car_models:
                url1 = f"https://www.avito.ru/{cit}/avtomobili/{firm}/{model}"
                await page.goto(
                    url1,
                    wait_until="domcontentloaded"
                )

                
                print("Ждём загрузки страницы...")
                await page.wait_for_timeout(1000) # даём время на первую загрузку

                # Прокручиваем страницу вниз, чтобы подгрузились объявления
                print("Прокручиваем страницу...")
                for _ in range(4):                    # можно увеличить до 6-8
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)
                
                # === Основной селектор для карточек на Авито ===
                cards = await page.locator('div[data-marker="item"]').all()
                
                print(f"\nНайдено объявлений: {len(cards)}")
                
                if len(cards) == 0:
                    print("Объявления не найдены! Делаем скриншот и сохраняем HTML...")

                    print("Объявления не найдены — возможно капча")
                    await check_for_captcha(page)   # используем нашу функцию


                    await page.screenshot(path="avito_error.png", full_page=True)
                    with open("avito_page.html", "w", encoding="utf-8") as f:
                        f.write(await page.content())
                    print("Файлы сохранены для анализа.")

                
                for i, card in enumerate(cards[:6]):   # берём первые 6 для примера
                    try:
                        print(f"\n{'='*60}")
                        print(f"Объявление №{i+1}")
                        
                        # Название
                        title = await card.locator('[data-marker="item-title"]').first.inner_text(timeout=1000)
                        print("Название:", title.strip())
                        
                        
                        # Цена
                        price_elem = card.locator('[data-marker="item-price"]')
                        price = await price_elem.first.inner_text(timeout=random.randint(1200,1600))
                        print("Цена:", price.strip())
                        
                        # Ссылка на объявление
                        link_elem = card.locator('a[data-marker="item-title"]').first
                        relative_link = await link_elem.get_attribute("href")
                        if relative_link:
                            full_link = "https://www.avito.ru" + relative_link
                            print("Ссылка:", full_link)
                            list_of_cars.append(full_link)
                        
                        spisok = await parse_avito_card(full_link, context_page=page)
                        data.append({"Название" : title.strip(),
                                    "Цена" : price.strip(),
                                    "Город" : cit,
                                    "Дата публикации": spisok["publish_date"],
                                    "Пробег" : spisok["mileage"],
                                    "Ссылка" :full_link})

                        
                    except Exception as e:
                        print(f"Ошибка при обработке объявления №{i+1}: {e}")
                        await check_for_captcha(page)
                
        await browser.close()

asyncio.run(main())



print(list_of_cars)

print(*data, sep='\n')
df = pd.DataFrame(data)
df = df[["Название", "Цена", "Город", "Дата публикации", "Пробег", "Ссылка"]]
print(df)
OUTPUT_EXCEL = "vse_tachki_mira.xlsx"
df.to_excel(OUTPUT_EXCEL, index=True)
print(f"Файл сохранён: {OUTPUT_EXCEL}\n")
