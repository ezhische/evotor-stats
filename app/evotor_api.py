import requests
import pandas as pd
import os

API_URL=os.getenv("EVOTOR_API_URL")

class EvotorAPI:
    """
    Class to work with Evotor stores api. 
    """
    def __init__(self, store_id:int, token:str):
        self.store_id = store_id
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.evotor.v2+json',
            'Content-Type': 'application/vnd.evotor.v2+json'
        }

    def get_items(self, from_date, to_date) -> pd.DataFrame:
        query = {'since': from_date , 'until': to_date}
        response = requests.get(
            f'{API_URL}/{self.store_id}/documents',
            headers=self.headers,
            params=query
        )
        try: 
            response.raise_for_status()
        except Exception as e:
            print(f"Error contacting api:{e}")
            return None
        daf = pd.DataFrame(response.json()['items'])
        try: 
            df = daf.loc[daf['type']=='SELL']
        except KeyError:
            print(f"No sells from {from_date} to {to_date}")
            df = None
        return df

    def get_cash(self, df:pd.DataFrame):
        """
        Get payments by cash
        """
        try:
            cash_total = sum(line[0]['sum'] for line in df['body'].apply(lambda x: x.get('payments', [])).values if line and line[0]['type'] == 'CASH')
        except (TypeError, KeyError):
            cash_total = 0

        return cash_total

    def get_discount(self, df):
        try:
            sums = df['body'].apply(lambda x: x.get('sum', 0)).values
            result_sums = df['body'].apply(lambda x: x.get('result_sum', 0)).values
        except TypeError:
            return 0

        discount_total = sum(int(s - rs) for s, rs in zip(sums, result_sums) if s != rs)
        return int(round(discount_total))
    def get_group_id(self, name):
        response = requests.get(
            f'{API_URL}/{self.store_id}/product-groups',
            headers=self.headers
        )
        prod = pd.DataFrame(response.json()['items'])
        groups = prod.set_index('name')['id'].to_dict()
        return groups.get(name)

    def get_product_list(self, group_id):
        response = requests.get(
            f'{API_URL}/{self.store_id}/products',
            headers=self.headers
        )
        prod = pd.DataFrame(response.json()['items'])
        listof = prod.loc[prod['parent_id'] == group_id, 'id'].tolist()
        return listof