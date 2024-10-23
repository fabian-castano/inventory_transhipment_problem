import json
from datetime import datetime
import requests
import os
import pandas as pd
import functools
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from app.src.loggin import logger
from typing import List, Dict, Set

_DEFAULT_TIMEOUT_SECONDS = 30


def _get_default_retries():
    """
    Create default retries requests object
    :return: Retry requests object
    """
    return requests.adapters.Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504])


class MLOpsClient:

    def __init__(self, url, api_key):
        self.url = url
        self.api_key = api_key

    def get_waste_by_age(self, todays_date: datetime, warehouse_code: str = None, limit: int = 5000,
                         fields=None) -> dict:
        if fields is None:
            fields = ["sku_code",
                      "waste_per_age"]

        complete_response = []
        pg = 0
        while True:
            pg += 1
            payload = json.dumps({
                "model": "waste_per_age",
                "vertical": "planning",
                "page": pg,
                "limit": limit,
                "query": {
                    "condition_type": "AND",
                    "conditions": [
                        {
                            "field": "created_at",
                            "value": todays_date,
                            "comparison": "gte"
                        },
                        {
                            "field": "warehouse_code",
                            'value': warehouse_code,
                            'comparison': 'e'
                        }

                    ]
                },
                "fields_to_return": fields
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.api_key
            }

            response = requests.request("GET", self.url, headers=headers, data=payload)
            complete_response += response.json()["result"]
            if len(response.json()["result"]) == 0:
                break

        return {v['sku_code']: v['waste_per_age'] for v in complete_response}

    def get_forecast_errors(self
                            , warehouse_code: str = None
                            , limit: int = 5000
                            , fields=None) -> dict:
        if fields is None:
            fields = ["sku_code",
                      "forecast_error_model"]

        complete_response = []
        pg = 0
        while True:
            pg += 1
            payload = json.dumps({
                "model": "forecast_errors",
                "vertical": "planning",
                "page": pg,
                "limit": limit,
                "query": {
                    "condition_type": "AND",
                    "conditions": [
                        {
                            "field": "warehouse_code",
                            'value': warehouse_code,
                            'comparison': 'e'
                        }

                    ]
                },
                "fields_to_return": fields
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.api_key
            }

            response = requests.request("GET", self.url, headers=headers, data=payload)
            complete_response += response.json()["result"]
            if len(response.json()["result"]) == 0:
                break
        return {v['sku_code']: v['forecast_error_model']['params'] for v in complete_response}

    def get_lead_times(self
                       , warehouse_code: str = None
                       , execution_date: str = None
                       , limit: int = 500
                       , fields=None) -> dict:
        if fields is None:
            fields = ["sku_code",
                      "created_at",
                      "lead_time",
                      "day_of_week",
                      "warehouse_code",
                      "supplier_id"]

        pg = 0
        complete_response = []
        while True:
            pg += 1
            payload = json.dumps({
                "model": "lead_times",
                "vertical": "planning",
                "page": pg,
                "limit": limit,
                "query": {
                    "condition_type": "AND",
                    "conditions": [

                        {
                            "field": "warehouse_code",
                            'value': warehouse_code,
                            'comparison': 'e'
                        },
                        {
                            "field": "day_of_week",
                            "value": int(datetime.strptime(execution_date, "%Y-%m-%d").weekday()),
                            "comparison": "e"
                        }

                    ]
                },
                "fields_to_return": fields
            })

            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.api_key
            }
            logger.info(f"Payload: {payload}")
            response = requests.request("GET", self.url, headers=headers, data=payload)
            logger.info(f"Response: {response.json()}")
            complete_response += response.json()["result"]
            if len(response.json()["result"]) == 0:
                break

        lead_time_models = {}
        for v in complete_response:
            lead_time_models[(v['sku_code'], int(v['supplier_id']))] = {int(ind): val for ind, val in
                                                                        v["lead_time"]["prob_value_pairs"].items()}

        return lead_time_models

    def get_costs(self
                  , warehouse_code: str = None
                  , purchase_type:  str = None
                  , limit: int = 5000
                  , fields=None) -> dict:
        if fields is None:
            fields = ["sku_code",
                      "price_per_unit",
                      "percentage_cost_per_unit_excess",
                      "percentage_cost_per_unit_shortage",
                      "percentage_cash_margin_per_unit"]

        pg = 0
        complete_response = []
        while True:
            pg += 1
            payload = json.dumps({
                "model": "inventory_costs",
                "vertical": "planning",
                "page": pg,
                "limit": limit,
                "query": {
                    "condition_type": "AND",
                    "conditions": [
                        {
                            "field": "warehouse_code",
                            'value': warehouse_code,
                            'comparison': 'e'
                        },
                        {
                            "field": "purchase_type",
                            "value": purchase_type,
                            "comparison": "e"
                        }
                    ]
                },
                "fields_to_return": fields
            })

            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.api_key
            }
            #print(payload)


            response = requests.request("GET", self.url, headers=headers, data=payload)
            # print curl
            #print(response.json())

            complete_response += response.json()["result"]
            if len(response.json()["result"]) == 0:
                break
        complete_response = {v['sku_code']: v for v in complete_response}
        complete_response = {k: {'percentage_cost_per_unit_excess': float(v['percentage_cost_per_unit_excess']),
                                 'percentage_cost_per_unit_shortage': float(v['percentage_cost_per_unit_shortage']),
                                 'percentage_cash_margin_per_unit': float(v['percentage_cash_margin_per_unit']),
                                 'price_per_unit': float(v['price_per_unit'])} for k, v in complete_response.items()}
        return complete_response


    def get_waste_per_age(self
                          , todays_date: datetime
                          , warehouse_code: str = None
                          , limit: int = 5000,
                     fields=None) -> dict:
        if fields is None:
            fields = ["sku_code",
                      "waste_per_age"]

        complete_response = []

        pg = 0
        while True:
            pg += 1
            payload = json.dumps({
                "model": "waste_per_age",
                "vertical": "planning",
                "page": pg,
                "limit": limit,
                "query": {
                    "condition_type": "AND",
                    "conditions": [
                        {
                            "field": "created_at",
                            "value": todays_date,
                            "comparison": "gte"
                        },
                        {
                            "field": "warehouse_code",
                            'value': warehouse_code,
                            'comparison': 'e'
                        }

                    ]
                },
                "fields_to_return": fields
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.api_key
            }

            response = requests.request("GET", self.url, headers=headers, data=payload)
            complete_response += response.json()["result"]
            if len(response.json()["result"]) == 0:
                break

        return {v['sku_code']: v['waste_per_age'] for v in complete_response}

class AvailableStockPRApiClient:
    def __init__(
            self,
            url: str,
            auth_url: str,
            user: str,
            password: str,
    ):
        self._url = url
        self._auth_url = auth_url
        self._user = user
        self._password = password
        self.session = requests.Session()
        self.session.request = functools.partial(
            self.session.request,
            timeout=_DEFAULT_TIMEOUT_SECONDS)
        retries = _get_default_retries()

        self.session.mount('http://',
                           requests.adapters.HTTPAdapter(max_retries=retries))
        self.session.mount('https://',
                           requests.adapters.HTTPAdapter(max_retries=retries))

    def _authenticate(self):
        basic = HTTPBasicAuth(self._user, self._password)
        url = f'{self._auth_url}/ops-public-api/v1/pri/fed/ops-cactus/api/v2/auth/token'
        res = self.session.post(url, auth=basic)
        res.raise_for_status()
        json_res = res.json()
        self.session.headers.update({'Authorization': f'Bearer {json_res["token"]}'})

    def get_available_stock(
            self,
            products_ids: list
    ) -> dict:
        # Authenticate always as there's no way to check validity of last token
        self._authenticate()
        url = f'{self._url}/pr-stock-available/v1/stocks/wh-product-id'
        requests_response = self.session.post(url, json=products_ids)
        requests_response.raise_for_status()
        return requests_response.json()

class InTransitStockPRApiClient:
    def __init__(
            self,
            url: str,
            auth_url: str,
            user: str,
            password: str,
    ):
        self._url = url
        self._auth_url = auth_url
        self._user = user
        self._password = password
        self.session = requests.Session()
        self.session.request = functools.partial(
            self.session.request,
            timeout=_DEFAULT_TIMEOUT_SECONDS)
        retries = _get_default_retries()

        self.session.mount('http://',
                           requests.adapters.HTTPAdapter(max_retries=retries))
        self.session.mount('https://',
                           requests.adapters.HTTPAdapter(max_retries=retries))

    def _authenticate(self):
        basic = HTTPBasicAuth(self._user, self._password)
        url = f'{self._auth_url}/ops-public-api/v1/pri/fed/ops-cactus/api/v2/auth/token'
        res = self.session.post(url, auth=basic)
        res.raise_for_status()
        json_res = res.json()
        self.session.headers.update({'Authorization': f'Bearer {json_res["token"]}'})

    def get_in_transit_stock(
            self,
            skus: list,
            warehouse: str,
            initial_date: str,
            final_date: str,
            excluded_types=None

    ) -> dict:
        # Authenticate always as there's no way to check validity of last token
        self._authenticate()
        url = f'{self._url}/pr-purchases/orders/apricot-query/stock-in-transit'

        message = {
            'skus': skus,
            'from': initial_date[:10],  # YYYY-MM-DD
            'to': final_date[:10],  # YYYY-MM-DD
            'warehouse': warehouse,
            "excludeTypes": excluded_types

        }


        logger.debug(f"Requesting in transit stock with message: {message}")
        requests_response = self.session.post(url, json=message)
        requests_response.raise_for_status()
        logger.debug(f"Response: {requests_response.json()}")
        return requests_response.json()


# ================================================================================
# ================================================================================
# ================================================================================
# service.py
# ================================================================================
# ================================================================================
# ================================================================================

class InTransitStockService:
    def __init__(self, in_transit_stock_api_client: InTransitStockPRApiClient):
        self._available_stock_api_client = in_transit_stock_api_client

    def get_in_transit_stock(self, sku_ids: list
                             , warehouse: str
                             , initial_date: str
                             , final_date: str
                             , excluded_types = None
                             ) -> dict:
        pr_res = self._available_stock_api_client.get_in_transit_stock(
            sku_ids,
            warehouse,
            initial_date,
            final_date
            , excluded_types
        )
        in_transit_stock = {}
        for current_pr_product in pr_res:
            in_transit_stock.update({current_pr_product['sku']: current_pr_product['quantity']})

        return in_transit_stock

    def get_detailed_in_transit_stock(self, sku_ids: List[str]
                             , warehouse: str
                             , initial_date: str
                             , final_date: str
                             , excluded_types:List[str] = None
                             ) -> dict:
        in_transit_by_date = {}

        for fecha in pd.date_range(start=initial_date, end=final_date):
            df = self.get_in_transit_stock(sku_ids
                                          , warehouse
                                          , fecha.strftime('%Y-%m-%d')
                                          , fecha.strftime('%Y-%m-%d')
                                          , excluded_types
                                          )
            in_transit_by_date[fecha.strftime('%Y-%m-%d')] = df

        in_transit_by_sku = {}
        for fecha in in_transit_by_date:
            for sku in in_transit_by_date[fecha].keys():
                if sku not in in_transit_by_sku:
                    in_transit_by_sku[sku] = {}
                in_transit_by_sku[sku][fecha] = in_transit_by_date[fecha][sku]
        return in_transit_by_sku


class AvailableStockService:
    def __init__(self, available_stock_api_client: AvailableStockPRApiClient):
        self._available_stock_api_client = available_stock_api_client

    def get_available_stock(self, warehouse: str, products_ids: List[int]) -> dict:
        pr_res = self._available_stock_api_client.get_available_stock(
            products_ids
        )
        available_stock = {}
        products_ids_set = set(products_ids)
        for current_pr_product in pr_res:
            if current_pr_product['warehouse'] == warehouse and \
                    current_pr_product['whProductId'] in products_ids_set:
                if current_pr_product['whProductId'] not in available_stock:
                    available_stock[current_pr_product['sku']] = {}

                if current_pr_product['source'] not in available_stock[current_pr_product['sku']]:
                    available_stock[current_pr_product['sku']][current_pr_product['source']] = 0
                # save one record by product and source
                available_stock[current_pr_product['sku']][current_pr_product['source']] += current_pr_product[
                    'theoreticalInventory']


        for product,values in available_stock.items():
            available_stock[product] = sum(list(values.values()))

        return available_stock


class DemandPlanningForecastClient:

    def __init__(self, url, api_key):
        self.url = url
        self._token = api_key

        self.content_type = 'application/json'
        self.session = requests.Session()
        self.session.request = functools.partial(self.session.request,
                                                 timeout=_DEFAULT_TIMEOUT_SECONDS)
        retries = _get_default_retries()

        self.session.mount('http://',
                           requests.adapters.HTTPAdapter(max_retries=retries))
        self.session.mount('https://',
                           requests.adapters.HTTPAdapter(max_retries=retries))

        self.session.headers.update({'Content-Type': 'application/json'})

        self.session.headers.update({"X-API-TOKEN": self._token})

    def get_batch_forecasts_skus(self, params: dict):

        url = self.url + '/forecasts-service/cms/forecasts/daily-forecast/list'

        payload = json.dumps({
            'start_date': params['start_date'],
            'end_date': params['end_date'],
            'region': params['region_code'],
            'warehouse': params['warehouse_code'],
            'product_ids': params['product_ids']

        })
        print(payload)


        logger.info(f"payload: {payload}")
        logger.info(f" ==================================== token: {self._token} ==================================== ")

        requests_response = self.session.post(url
                                              , data=payload
                                              ).json()

        forecast = {}
        logger.info(f"requests_response: {requests_response}")
        for forecast_item in requests_response:
            forecast[forecast_item['id']] = {}
            for forecast_date in forecast_item['forecastDates']:
                forecast[forecast_item['id']][forecast_date['forecastDate']] = forecast_date['quantity']
        return forecast

