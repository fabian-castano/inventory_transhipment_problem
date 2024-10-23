import json
import math
import os
import pandas as pd
from app.src.loggin import logger
from app.src.classes import TranshipmentProblem,Product
from app.src.db_connector import get_database_connector_arn, DatabaseConnector
from app.src.container import Container

def run(event: dict):
    """
    :param event: dict with the information required to run the solver step
    :return:
    """
    logger.info("Running solver step")
    # Load the transhipment problem
    c = Container()
    """
    mlops_client = c.get_mlops_client()
    demand_forecast = c.get_dp_forecast_client()
    demand_forecast.get_batch_forecasts_skus()

    problem = TranshipmentProblem()
    problem.execution_id = event['execution_id']
    problem.origin_warehouse = event['origin_warehouse']
    problem.destination_warehouse = event['destination_warehouse']
    problem.execution_date = event['execution_date']
    problem.transhipment_lead_time_probability = event['transhipment_lead_time_probability']

    for p in products:
        product = Product()
        product.sku = p['sku']
        product.warehouse = p['warehouse']
        product.desired_service_level = p['desired_service_level']
        product.days_to_next_review = p['days_to_next_review']
        product.units_per_product_dim = p['units_per_product_dim']
        product.supplier_dim_to_product_dim_conversion_factor = p['supplier_dim_to_product_dim_conversion_factor']
        product.current_inventory = p['current_inventory']
        product.detailed_incoming_inventory = p['detailed_incoming_inventory']
        product.forecast = p['forecast']
        product.forecast_error_model = p['forecast_error_model']
        product.current_price_per_unit = p['current_price_per_unit']
        product.percentage_cost_per_unit_excess = p['percentage_cost_per_unit_excess']
        product.percentage_cost_per_unit_shortage = p['percentage_cost_per_unit_shortage']
        product.in_superwarehouse = p['in_superwarehouse']
        product.add_supplier(supplier)
        problem.add_origin_product(product)

    for p in destination_products:
        product = Product()
        product.sku = p['sku']
        product.warehouse = p['warehouse']
        product.desired_service_level = p['desired_service_level']
        product.days_to_next_review = p['days_to_next_review']
        product.units_per_product_dim = p['units_per_product_dim']
        product.supplier_dim_to_product_dim_conversion_factor = p['supplier_dim_to_product_dim_conversion_factor']
        product.current_inventory = p['current_inventory']
        product.detailed_incoming_inventory = p['detailed_incoming_inventory']
        product.forecast = p['forecast']
        product.forecast_error_model = p['forecast_error_model']
        product.current_price_per_unit = p['current_price_per_unit']
        product.percentage_cost_per_unit_excess = p['percentage_cost_per_unit_excess']
        product.percentage_cost_per_unit_shortage = p['percentage_cost_per_unit_shortage']
        product.in_superwarehouse = p['in_superwarehouse']
        problem.add_destination_product(product)
    """