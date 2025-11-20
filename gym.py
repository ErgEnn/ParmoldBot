import random
from datetime import datetime, timedelta
import requests
import pytz
import logging

PROMETHEUS_URL = 'http://prometheus:9090'


def round_time_to_nearest_quarter_hour(dt=None):
    if dt is None:
        tz = pytz.timezone('Europe/Tallinn')
        dt = datetime.now(tz)
    # Zero out the seconds and microseconds
    dt = dt.replace(second=0, microsecond=0)
    minute = (dt.minute // 15) * 15
    if dt.minute % 15 >= 8:
        minute += 15
    if minute >= 60:
        minute = 0
        dt += timedelta(hours=1)
    dt = dt.replace(minute=minute)
    return dt


def get_same_weekday_dates(current_date, weeks_back=2):
    dates = []
    for i in range(1, weeks_back + 1):
        date = current_date - timedelta(weeks=i)
        dates.append(date)
    return dates


def get_max_people_count_for_day(date):
    try:
        start_time = datetime.combine(date, datetime.min.time()).timestamp()
        end_time = datetime.combine(date + timedelta(days=1), datetime.min.time()).timestamp()
        query = 'sum(max_over_time(people_count[1d]))'
        params = {
            'query': query,
            'start': start_time,
            'end': end_time,
            'step': '1d',
        }
        response = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params=params)
        data = response.json()
        if data['status'] == 'success' and len(data['data']['result']) == 1:
            return int(data['data']['result'][0]['value'][1])
        return 0
    except Exception as e:
        logging.error(f"Error fetching data for date {date}: {e}")
        return 0


def get_average_people_count_at_time(time):
    try:
        timestamp = time.timestamp()
        query = 'sum(people_count)'
        params = {
            'query': query,
            'time': timestamp,
        }
        response = requests.get(f'{PROMETHEUS_URL}/api/v1/query', params=params)
        data = response.json()

        if data['status'] == 'success' and len(data['data']['result']) == 1:
            cnt = int(data['data']['result'][0]['value'][1])
            if cnt == 0:
                logging.debug(params)
                logging.debug(data)
            return cnt
        logging.debug(params)
        logging.debug(data)
        return 0
    except Exception as e:
        logging.error(f"Error fetching average people count at time {time}: {e}")
        return 0


async def try_handle_mhm(message):
    if random.random() > 0.05:
        # allow using mhm more
        return

    if 'mhm' not in message.content.lower():
        return

    current_time = round_time_to_nearest_quarter_hour()
    if message.author.id == 145929101482524672:
        sydney_timezone = pytz.timezone('Australia/Sydney')
        sydney_time = datetime.now(sydney_timezone)
        current_time = round_time_to_nearest_quarter_hour(sydney_time)

    dates = get_same_weekday_dates(current_time)

    current_counts = []
    daily_maxima = []
    for date in dates:
        max_count = get_max_people_count_for_day(date)
        daily_maxima.append(max_count)
        current_count = get_average_people_count_at_time(date)
        current_counts.append(current_count)

    average_daily_max = sum(daily_maxima) / len(daily_maxima)
    average_daily_current = sum(current_counts) / len(current_counts)

    percentage = average_daily_current / average_daily_max

    if percentage > 0.5:
        await message.reply(f'Ta pigem on jõuksis! (ratio={percentage:.2f})')
    else:
        await message.reply(f'Ta pigem pole jõuksis! (ratio={percentage:.2f})')
