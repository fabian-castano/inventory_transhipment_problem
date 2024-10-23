import json
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()


class Container:
    def __init__(self):
        self._mlops_client = None
        self._dwd_connector = None
        self._dw_connector = None
        self._available_stock_service = None
        self._in_transit_stock_service = None
        self._dp_forecast_client = None

    def get_mlops_client(self):
        if not self._mlops_client:
            from app.src.api_clients import MLOpsClient
            self._mlops_client = MLOpsClient(os.environ['MLOPS_API_URL'], os.environ['MLOPS_API_KEY'])
        return self._mlops_client

    def get_dwd_connector(self):
        from app.src.db_connector import DatabaseConnector, get_database_connector_arn
        if not hasattr(self, '_dwd_connector'):
            try:
                self._dwd_connector = DatabaseConnector(os.getenv('DWD_NAME'),
                                                        os.getenv('DWD_HOST'),
                                                        os.getenv('DWD_PORT'),
                                                        os.getenv('DWD_USER'),
                                                        os.getenv('DWD_PASSWORD'))
            except Exception as e:
                # logger.exception(e)
                self._dwd_connector = get_database_connector_arn(os.getenv('AWS_REGION', 'us-east-1'),
                                                                 os.getenv('ARN_DWD'))
            else:
                pass

        return self._dwd_connector

    def get_dw_connector(self):
        from app.src.db_connector import DatabaseConnector, get_database_connector_arn
        if not hasattr(self, '_dw_connector'):
            try:
                self._dw_connector = DatabaseConnector(os.getenv('DW_NAME'),
                                                       os.getenv('DW_HOST'),
                                                       os.getenv('DW_PORT'),
                                                       os.getenv('DW_USER'),
                                                       os.getenv('DW_PASSWORD'))
            except Exception as e:
                # logger.exception(e)
                self._dw_connector = get_database_connector_arn(os.getenv('AWS_REGION', 'us-east-1'),
                                                                os.getenv('ARN_DW'))
            else:
                pass
        return self._dw_connector

    def available_stock_service(self):
        from app.src.api_clients import AvailableStockService, AvailableStockPRApiClient
        if self._available_stock_service is None:
            ass = AvailableStockPRApiClient(
                os.getenv('INVENTORY_SERVICE_URL'),
                os.getenv('FEDERATE_URL'),
                os.environ['CACTUS_USER'],
                os.environ['CACTUS_PASS']
            )
            self._available_stock_service = AvailableStockService(ass)
        return self._available_stock_service

    def in_transit_stock_service(self):
        from app.src.api_clients import InTransitStockPRApiClient, InTransitStockService
        if self._in_transit_stock_service is None:
            itss = InTransitStockPRApiClient(
                os.getenv('INVENTORY_SERVICE_URL'),
                os.getenv('FEDERATE_URL'),
                os.environ['CACTUS_USER'],
                os.environ['CACTUS_PASS']
            )
            self._in_transit_stock_service = InTransitStockService(itss)
        return self._in_transit_stock_service

    def get_dp_forecast_client(self):
        if not self._dp_forecast_client:
            from app.src.api_clients import DemandPlanningForecastClient
            self._dp_forecast_client = DemandPlanningForecastClient(os.environ['FEDERATE_URL']
                                                                    , os.environ['DP_FORECAST_SERVICE_TOKEN']
                                                                    )
        return self._dp_forecast_client


if __name__ == "__main__":
    c = Container()

    # Example stock service
    #stock_service = c.available_stock_service()
    #print(stock_service.get_available_stock('STA', [628490, 654588]))

    # example in transit stock
    #in_trasit_service=c.in_transit_stock_service()
    #print(in_trasit_service.get_detailed_in_transit_stock(['SPO-FRU1-CAT106989-440078:1120054:1120053:612129', 'SPO-FRU1-CAT107282-60969:126713:126712:74194', 'SPO-FRU1-CAT107269-62061:129959:129958:75842','SPO-FRU1-CAT107282-60969:126713:126712:74194',"SPO-FRU1-CAT2-60514:125459:125458:73648"], 'VLP', '2024-10-03', '2024-10-10',excluded_types=None))

    # example forecast client
    """forecast_client = c.get_dp_forecast_client()
    params = {

        'warehouse_code': 'SPN',
        'region_code': 'SPO',
        "start_date": "2024-10-06",
         "end_date": "2024-12-04",
        'product_ids': [446402, 543307, 642925, 609712, 273240, 446396, 622143]
    }
    forecast = forecast_client.get_batch_forecasts_skus(params)
    print(forecast)#"""

    # Forecast error
    mlopsclient = c.get_mlops_client()
    #print(mlopsclient.get_forecast_errors('SPN'))
    #print(mlopsclient.get_lead_times( 'SPN',datetime.now().strftime('%Y-%m-%d')))
    print(mlopsclient.get_costs('GRU','out'))


