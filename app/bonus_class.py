#!/usr/bin/python3
# -*- coding: utf-8 -*- 
import pygsheets
import os
import json
from datetime import datetime
import argparse
import sys
import pytz
import pandas as pd
from calendar_manager import CalendarManager
from evotor_api import EvotorAPI, API_URL
from typing import List

KEY_FILE = os.getenv("GOOGLE_KEY_FILE_NAME")
STORE_ID = os.getenv("EVOTOR_STORE_ID")
TOKEN = os.getenv("EVOTOR_API_TOKEN")
NAMES = json.loads(os.getenv("BARTENDERS_LIST"))
#TODO: Подумать как лучше сделать с группами исключений, пока хардкодинг 2х категорий
#EXCEPT_GROPS = json.loads(os.getenv("EXCEPT_GROUPS"))
PRIME_MIN = float(os.getenv("PRIME_MIN"))

def timestamp(dt:datetime)->int:
    tz = pytz.timezone('Europe/Moscow')
    return int(dt.replace(tzinfo=tz).timestamp() * 1000)

def total_sum(df:pd.DataFrame) ->float:
    try:
      return sum(i['result_sum'] for i in df['body'].values if isinstance(i, dict))
    except:
      return 0	

def extractdigits(lst) -> List:
    return [[el] for el in lst]

def grill_snaks(df:pd.DataFrame, snaks:str, grill:str) -> List:
    try:
      snaks_sum = sum(pos['result_sum'] for line in df['body'].values.tolist() for pos in line['positions'] if pos.get('product_id') in snaks)
      grill_sum = sum(pos['result_sum'] for line in df['body'].values.tolist() for pos in line['positions'] if pos.get('product_id') in grill)
    except:
      snaks_sum=0
      grill_sum=0
    return [int(round(snaks_sum)), int(round(grill_sum))]


def save_table(data, cell, addr=0):
    if addr != 0:
        addr = cell+ str(addr)
    else:
      addr = cell + str(stat_config['start'] + 1)
    wks.update_values(addr, extractdigits(data))

def get_user_input() -> dict:
    try:
        year = int(input('Введите год: '))
        month = int(input('Введите месяц: '))
        start = int(input('Дата начала: '))
        end = int(input('Дата окончания: ')) + 1

        if start > end - 1:
            print("Дата начала раньше даты конца")
            sys.exit(1)

        return {'year': year, 'month': month, 'start': start, 'end': end}
    except ValueError:
        print("Invalid input. Please enter numeric values.")
        sys.exit(1)

def get_params():
    parser = argparse.ArgumentParser(description='Process command line arguments.')

    parser.add_argument('--year', type=int, help='Year')
    parser.add_argument('--month', type=int, help='Month')
    parser.add_argument('--start', type=int, help='Start date')
    parser.add_argument('--end', type=int, help='End date')

    args = parser.parse_args()

    stat_config = {
        'year': args.year,
        'month': args.month,
        'start': args.start,
        'end': args.end + 1 if args.end is not None else None
    }
    # If config is not full get user input
    if not all(value is not None for value in stat_config.values()):
        return get_user_input()
    return stat_config

if __name__ == '__main__':
    #Connect to APIs
    calendar = CalendarManager(KEY_FILE,NAMES)
    api = EvotorAPI(STORE_ID,TOKEN)
    gc = pygsheets.authorize(service_file=KEY_FILE)

    # Initialise Lists and Variables
    stat_config = get_params()
    all_primes = {}
    sum_list, snack_list, grill_list, cash_list, discount_list, barmen_list, primes, output = [], [], [], [], [], [], [],[]
    grand_total, cash_total, prime_vanya, prime_vlad, prime_lesha = 0.0,  0.0,  0.0,  0.0,  0.0
    snaks = api.get_product_list(api.get_group_id('Снэки'))
    grill = api.get_product_list(api.get_group_id('Гриль'))
    header = ('Выручка', 'Наличные', 'Скидки', 'Снеки', 'Гриль', 'Премия', 'Бармен')
    formatted_header = '{:^12}{:^10}{:^10}{:^10}{:^10}{:^10}{:^20}'.format(*header)
    output.append(formatted_header)
    #Set Working Sheet
    sh = gc.open('Kitchen Test')
    wks = sh[(stat_config['month'] - 1 + 12 * (stat_config['year'] - 2022))]

    try:
        shed = calendar.get_schedule(
            datetime(stat_config['year'],stat_config['month'],stat_config['start']), 
            datetime(stat_config['year'], stat_config['month'], (stat_config['end']- 1))
            )
    except ValueError:
        print("Дата не существует")
        sys.exit(1)

    for idx, date in enumerate(range(stat_config['start'], stat_config['end'])):
        from_date = timestamp(datetime(stat_config['year'], stat_config['month'], date))
        to_date = timestamp(datetime(stat_config['year'], stat_config['month'], date, 23, 59, 59))
        barmen_list.append(shed.get(str(datetime(stat_config['year'], stat_config['month'], date).date()), ' '))
        df = api.get_items(from_date, to_date)

        total = total_sum(df)
        cash = api.get_cash(df)
        discount = api.get_discount(df)
        misc = grill_snaks(df, snaks, grill)
        sum_list.append(int(total))
        snack_list.append(int(misc[0]))
        grill_list.append(int(misc[1]))
        cash_list.append(int(cash))
        discount_list.append(int(discount))
        grand_total+= total_sum(df)
        cash_total += cash

        subtotal = total - discount - int(misc[0]) - int(misc[1])
        prime = (subtotal * 0.09) if subtotal > PRIME_MIN else 0

        output.append(f"{total:^12.2f}{cash:^10}{discount:^10}{misc[0]:^10}{misc[1]:^10}{int(prime):^10}{barmen_list[idx]:^20}")
        for barmen in barmen_list[idx].split(' '):
            all_primes.setdefault(barmen, 0)
            all_primes[barmen] += prime / len(barmen_list[idx].split(' '))

    primes.extend([int(all_primes.get('Влад')), int(all_primes.get('Ваня')), int(all_primes.get('Леша'))])
    output.append(f"Итого Выручка: {grand_total:.2f}, Наличные: {cash_total:.2f}")
    output.append("Премии:")
    for name in all_primes.keys():
        output.append(f"{name}: {int(all_primes.get(name))}")
    output.append(f"Итого: {int(sum(all_primes.values()))}")
    for line in output:
        print(line)
    save_table(sum_list, 'E')
    save_table(snack_list, 'F')
    save_table(grill_list, 'G')
    save_table(cash_list, 'L')
    save_table(discount_list, 'R')
    save_table(barmen_list, 'K')
    save_table(primes, 'G', 38)
