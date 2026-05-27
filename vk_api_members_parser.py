import vk_api
import time
import pandas as pd
from datetime import datetime
from vk_api.exceptions import ApiError
import random

# ==================== НАСТРОЙКИ ====================
#club221866393
#club56338600
#panautoo
#club60456834
#club23636659
#autoru_news
data_clean = pd.DataFrame()
city_counts_df = pd.DataFrame()
# ===================================================

def calculate_age(bdate: str):
        if not bdate:
            return None
        try:
            day, month, year = map(int, bdate.split('.'))
            return datetime.now().year - year
        except:
            return None


def get_last_seen(last_seen_dict):

    if not last_seen_dict or 'time' not in last_seen_dict:
        return "Неизвестно"
    try:
        timestamp = last_seen_dict['time']
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return "Неизвестно"

class MembersParser():
    def __init__(self, group_screen_name):
        self.group_screen_name = group_screen_name
        self.OUTPUT_EXCEL = f"{group_screen_name}_vk_members_full.xlsx"



    def parse(self):
        TOKEN = "6656695b6656695b6656695bc5651766c4666566656695b0c5e26dddb6e1257f01f1f17"

        vk_session = vk_api.VkApi(token=TOKEN)
        vk = vk_session.get_api()


        group_info = vk.groups.getById(group_ids=GROUP_SCREEN_NAME)
        group_id = group_info[0]['id']
        print(f"ID группы: {group_id}")

        all_members = []
        offset = 0
        COUNT = 1000


        flood_sleep = 30
        max_flood_retries = 5
        flood_retries = 0

        while True:
            try:
                response = vk.groups.getMembers(
                    group_id=group_id,
                    count=COUNT,
                    offset=offset,
                    fields="sex, bdate, city, last_seen",
                )

                items = response.get("items", [])
                all_members.extend(items)

                print(f"Загружено: {len(all_members)} участников")

                # если пришло меньше COUNT, значит это последняя пачка
                if len(items) < COUNT:
                    break

                offset += COUNT

                # обычная пауза между успешными запросами
                time.sleep(random.uniform(1.5, 3.0))

                # если запрос прошёл успешно — сбрасываем счётчик flood-ошибок
                flood_retries = 0

            except ApiError as e:
                if e.code == 6:
                    print("Лимит запросов. Ждём 3 секунды...")
                    time.sleep(3)
                    continue

                elif e.code == 9:
                    flood_retries += 1

                    if flood_retries > max_flood_retries:
                        print("Слишком много Flood control ошибок.")
                        print("Останавливаем загрузку и сохраняем то, что уже удалось получить.")
                        break

                    wait_time = flood_sleep * flood_retries
                    print(f"Flood control. Ждём {wait_time} секунд и пробуем снова...")

                    time.sleep(wait_time)
                    continue

                elif e.code == 15:
                    print("Ошибка: группа скрыла список участников.")
                    print("VK API не даёт получить участников этой группы.")
                    return

                else:
                    print("Ошибка API:", e)
                    print("Останавливаем загрузку и сохраняем то, что уже удалось получить.")
                    break


        data = []
        for user in all_members:
            age = calculate_age(user.get('bdate'))
            sex_code = user.get('sex', 0)

            gender = {
                1: "Женский",
                2: "Мужской",
                0: "Не указан"
            }.get(sex_code, "Не указан")

            city = user.get('city', {})
            city_name = city.get('title') if isinstance(city, dict) else "Не указан"

            last_seen = get_last_seen(user.get('last_seen'))

            data.append({
                "vk_id": user['id'],
                "link": f"https://vk.com/id{user['id']}",
                "пол": gender,
                "возраст": age,
                "город": city_name,
                "последний_визит": last_seen
            })


        df = pd.DataFrame(data)
        self.members_df = df[["vk_id", "link", "пол", "возраст", "город", "последний_визит"]]



        print(f" Всего участников: {len(df)}")
        
    
    def to_excel(self, NotNull=False):
        if not NotNull:
            self.members_df.to_excel(f"{self.OUTPUT_EXCEL}", index=False)
            print(f"Файл сохранён: {self.OUTPUT_EXCEL}")
        else:
            self.members_not_null_df.to_excel(f"NotNull_{self.OUTPUT_EXCEL}", index=False)
            print(f"Файл сохранён: NotNull_{self.OUTPUT_EXCEL}")

    def with_age_and_city(self):
        df = self.members_df
        df_with_age = df[df['возраст'].notna() & (df['возраст'] > 18.0) & (df['возраст'] <= 70)]
        df_with_age_and_city = df_with_age[df_with_age['город'].notna()]
        self.members_not_null_df = df_with_age_and_city

def city_counts(df):
    global city_counts_df
    city_counts = df["город"].value_counts()
    city_counts_df = df["город"].value_counts().reset_index()
    city_counts_df.columns = ["город", "количество"]
    city_counts_df.to_excel("city_counts.xlsx", index=False)
    print("Файл сохранен: сity_counts.xlsx")

def concat_dfs(names):
    global data_clean
    dfs = []
    for name in names:
      df = pd.read_excel(name)
      dfs.append(df)
    data = pd.concat(dfs, ignore_index=True)
    data_clean = data.drop_duplicates(subset=["vk_id"])
    print(f"Количство совпадений: {len(data) - len(data_clean)}" )
    print(f"Итоговое количество участников: {len(data_clean)}")
    data_clean.to_excel("data_clean.xlsx", index=False)
    print("Файл сохранен: data_clean.xlsx")
