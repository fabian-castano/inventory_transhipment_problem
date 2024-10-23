import json
from dataclasses import dataclass
from dataclasses import field as default_factory
from typing import List, Dict

@dataclass
class Supplier:
    external_id: str
    lead_time_model: dict
    delay_model: dict = None

    def _to_dict(self):
        return {
            'external_id': self.external_id,
            'lead_time_model': self.lead_time_model,
            'delay_model': self.delay_model
        }


@dataclass
class Product:
    # add data hints
    """
    sku: str
    warehouse: str
    desired_service_level: float
    days_to_next_review: int
    units_per_product_dim: int
    supplier_dim_to_product_dim_conversion_factor: float
    current_inventory: int
    detailed_incoming_inventory: dict
    forecast: dict
    forecast_error_model: dict
    current_price_per_unit: float
    percentage_cost_per_unit_excess: float
    percentage_cost_per_unit_shortage: float
    in_superwarehouse: bool
    suppliers: list[Supplier]

    """

    sku: str
    warehouse: str
    desired_service_level: float
    days_to_next_review: int  # origin: days until next_purchase || destination: days until next transfer
    units_per_product_dim: int
    supplier_dim_to_product_dim_conversion_factor: float

    current_inventory: int
    detailed_incoming_inventory: dict

    forecast: dict
    forecast_error_model: dict

    current_price_per_unit: float
    percentage_cost_per_unit_excess: float
    percentage_cost_per_unit_shortage: float  # cash margin loss


    lots_expiration_by_date: dict = default_factory()

    mandatory: bool

    suppliers: List[Supplier] = default_factory()


    # remaining_shelf_life_units: dict = default_factory(dict)

    def add_supplier(self, supplier):
        self.suppliers.append(supplier)

    def _to_dict(self):
        return {
            'sku': self.sku,
            'warehouse': self.warehouse,
            'desired_service_level': self.desired_service_level,
            'days_to_next_review': self.days_to_next_review,
            'units_per_product_dim': self.units_per_product_dim,
            'supplier_dim_to_product_dim_conversion_factor': self.supplier_dim_to_product_dim_conversion_factor,
            'current_inventory': self.current_inventory,
            'detailed_incoming_inventory': self.detailed_incoming_inventory,
            'forecast': self.forecast,
            'forecast_error_model': self.forecast_error_model,
            'current_price_per_unit': self.current_price_per_unit,
            'percentage_cost_per_unit_excess': self.percentage_cost_per_unit_excess,
            'percentage_cost_per_unit_shortage': self.percentage_cost_per_unit_shortage,
            'mandatory': self.mandatory,
            'suppliers': [supplier._to_dict() for supplier in self.suppliers]
        }


@dataclass
class TranshipmentProblem:
    execution_id: str
    origin_warehouse: str
    destination_warehouse: str

    capacity_in_transport_units: int # the number of pallets that can be transported
    mandatory_closed_transport_units: int # the number of pallets that must contain a single product
    execution_date: str
    transhipment_lead_time_probability: dict
    origin_products: dict[str, Product] = default_factory()
    destination_products: dict[str, Product] = default_factory()



    def add_origin_product(self, product):
        self.origin_products[product.sku] = product

    def add_destination_product(self, product):
        self.destination_products[product.sku] = product

    def _to_dict(self):
        return {
            'execution_id': self.execution_id,
            'origin_warehouse': self.origin_warehouse,
            'destination_warehouse': self.destination_warehouse,
            'execution_date': self.execution_date,
            'transhipment_lead_time': self.transhipment_lead_time_probability,
            'mandatory_closed_transport_units': self.mandatory_closed_transport_units,
            'capacity_in_transport_units': self.capacity_in_transport_units,

            'origin_products': [product._to_dict() for _,product in self.origin_products.items()],
            'destination_products': [product._to_dict() for _,product in self.destination_products.items()]

        }

    def _to_json(self):
        return json.dumps(self._to_dict())




