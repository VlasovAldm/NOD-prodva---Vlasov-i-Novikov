import vk_api
import time
import pandas as pd
from datetime import datetime
from vk_api.exceptions import ApiError

# ==================== НАСТРОЙКИ ====================
GROUP_SCREEN_NAME = "club221866393"
OUTPUT_EXCEL = "vk_members_full.xlsx"
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


def main():
    TOKEN = "6656695b6656695b6656695bc5651766c4666566656695b0c5e26dddb6e1257f01f1f17"   

    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()


    group_info = vk.groups.getById(group_ids=GROUP_SCREEN_NAME)
    group_id = group_info[0]['id']
    print(f"ID группы: {group_id}")

    all_members = []
    offset = 0
    count = 1000



    # while True:
    #     try:
    #         response = vk.groups.getMembers(
    #             group_id=group_id,
    #             count=count,
    #             offset=offset,
    #             fields="sex, bdate, city, last_seen"   # нужные поля
    #         )

    #         items = response['items']
    #         all_members.extend(items)

    #         print(f"Загружено: {len(all_members)} участников")

    #         if len(items) < count:
    #             break

    #         offset += count
    #         time.sleep(0.4)

    #     except ApiError as e:
    #         if e.code == 6:
    #             print("Лимит запросов, ждём...")
    #             time.sleep(1)
    #             continue
    #         else:
    #             print("Ошибка API:", e)
    #             break
    try:
        response = vk.groups.getMembers(
            group_id=group_id ,
            count=count ,
            offset=offset,
            fields="sex, bdate, city, last_seen"   # нужные поля
        )
        
        items = response['items']
        all_members.extend(items)

        print(f"Получено {len(all_members)} участников")

        offset += count
        time.sleep(0.4)
    except ApiError as e:
        if e.code == 6:
            print("Превышен Лимит")
            time.sleep(1)
        else:
            print("Ошибка API:", e)



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
    df = df[["vk_id", "link", "пол", "возраст", "город", "последний_визит"]]
    
    df.to_excel(OUTPUT_EXCEL, index=False)


    print(f" Всего участников: {len(df)}")
    print(f"Файл сохранён: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()