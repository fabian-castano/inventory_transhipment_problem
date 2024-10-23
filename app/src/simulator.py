from dataclasses import dataclass
from datetime import datetime, timedelta

import scipy as sp
from app.src.loggin import logger
from app.src.ramdom_variates_generator import RandomVariates
from app.src.classes import Product, Supplier
import numpy as np
from abc import ABC, abstractmethod

from enum import Enum


def select_supplier(product: Product):
    # Defines the rule to be used to select the supplier
    # the most simple rule is to select the first supplier in the list of suppliers
    return product.suppliers[0]


def confidence_interval(data, confidence=0.95):
    a = 1.0 * np.array(data)
    n = len(a)
    m, se = np.mean(a), sp.stats.sem(a)
    h = se * sp.stats.t.ppf((1 + confidence) / 2., n - 1)
    return (m, h)


def estimate_sample_size(desired_halfwidth, confidence, sigma):
    z = sp.stats.norm.ppf(1 - (1 - confidence) / 2)
    return int((z * sigma / desired_halfwidth) ** 2)


class Simulator(ABC):

    def __init__(self, product: Product, is_origin: bool):
        self._stockout_units_by_quantity = None
        self._wasted_units_by_quantity = None
        pass

    @abstractmethod
    def simulate(self, sample_size: int = 10000):
        pass

    @property
    def stockout_units_by_quantity(self) -> dict:
        pass

    @property
    def wasted_units_by_quantity(self) -> dict:
        pass


class NonPerishableInventorySimulator(Simulator):
    product: Product
    forecast_error_model: dict
    lead_time_model: dict
    forecast_error_generator: RandomVariates
    lead_time_generator: RandomVariates
    forecast: dict
    detailed_incoming_inventory: dict
    _step_size: int
    _node_type: int

    def __init__(self, product: Product, is_origin: bool):
        super().__init__(product, is_origin)

        self.product = product
        self.forecast_error_model = self.product.forecast_error_model
        self.lead_time_model = select_supplier(self.product).lead_time_model
        self.forecast_error_generator = RandomVariates.get_distribution_by_code(
            self.forecast_error_model.get('distribution', None)).generator(self.forecast_error_model)
        self.lead_time_generator = RandomVariates.get_distribution_by_code(
            self.lead_time_model.get('distribution', None)).generator(self.lead_time_model)
        self.forecast = self.product.forecast
        self.detailed_incoming_inventory = self.product.detailed_incoming_inventory
        self._step_size = self.product.units_per_product_dim
        self._node_type = 1 if is_origin else 0

    def simulate(self, max_value_to_transfer: int = None, sample_size: int = 500):

        lead_time_vector = self.lead_time_generator.generate(0, sample_size) + self.product.days_to_next_review
        simulation_dates = [
            datetime.strftime(datetime.strptime(min(self.product.forecast.keys()), "%Y-%m-%d") + timedelta(days=i),
                              "%Y-%m-%d") for i in range(int(max(lead_time_vector)) + 1)]
        planning_horizon_length = len(simulation_dates)

        waste = np.zeros((sample_size, planning_horizon_length))
        lost_sales = np.zeros((sample_size, planning_horizon_length))
        stockouts = np.zeros((sample_size, planning_horizon_length))

        demand_scenarios = np.array([self.forecast_error_generator.generate(self.forecast.get(date, 0), sample_size) * (
                datetime.strptime(date, "%Y-%m-%d").weekday() != 6) for date in simulation_dates]).T

        total_demand = np.zeros(sample_size)
        for i, date in enumerate(simulation_dates):
            if date in self.product.forecast:
                total_demand += demand_scenarios[:, i] * (i <= lead_time_vector)
        interval = confidence_interval(total_demand)
        logger.info(
            f" the expected demand is {np.mean(total_demand)} and the halfwidth is {confidence_interval(total_demand)[1]}")
        if interval[0] != 0 and interval[1] / interval[0] * 100 >= 2:
            new_h = interval[0] * 0.02
            sample_size = estimate_sample_size(new_h, 0.95, np.std(total_demand))
            logger.warning(f"the sample size was increased to {sample_size}")
            lead_time_vector = self.lead_time_generator.generate(0, sample_size) + self.product.days_to_next_review
            simulation_dates = [
                datetime.strftime(datetime.strptime(min(self.product.forecast.keys()), "%Y-%m-%d") + timedelta(days=i),
                                  "%Y-%m-%d") for i in range(int(max(lead_time_vector)) + 1)]
            planning_horizon_length = len(simulation_dates)

            waste = np.zeros((sample_size, planning_horizon_length))
            lost_sales = np.zeros((sample_size, planning_horizon_length))
            stockouts = np.zeros((sample_size, planning_horizon_length))

            demand_scenarios = np.array(
                [self.forecast_error_generator.generate(self.forecast.get(date, 0), sample_size) * (
                        datetime.strptime(date, "%Y-%m-%d").weekday() != 6) for date in simulation_dates]).T

        Q_transfer = 0
        results_by_transfer = {}

        while True:
            inventory = np.zeros(sample_size) + self.product.current_inventory - Q_transfer * (
                1 if self._node_type == 1 else -1)

            for i, date in enumerate(simulation_dates):
                if date in self.product.forecast:
                    demand = demand_scenarios[:, i] * (i <= lead_time_vector)
                    lost_sales[:, i] = np.maximum(0, demand - inventory)
                    inventory = np.maximum(0, inventory - demand)
                    stockouts[:, i] = lost_sales[:, i] > 0
                    inventory += self.product.detailed_incoming_inventory.get(date, 0)
            new_res = {
                "lost_sales": np.mean(np.sum(lost_sales[:, :-1], axis=1)),
                "stockouts": np.mean(np.sum(stockouts[:, :-1], axis=1) > 0),
                "inventory": np.mean(inventory),
                'waste': 0
            }
            results_by_transfer[Q_transfer] = new_res
            if self._node_type == 1:
                if (new_res['stockouts'] > 1 - self.product.desired_service_level
                        or Q_transfer >= self.product.current_inventory):
                    break
            else:
                if new_res['stockouts'] < 1 - self.product.desired_service_level:
                    break

            Q_transfer += self._step_size

        self._stockout_units_by_quantity = {k: float(v['lost_sales']) for k, v in results_by_transfer.items()}
        self._wasted_units_by_quantity = {k: float(v['waste']) for k, v in results_by_transfer.items()}

    @property
    def stockout_units_by_quantity(self) -> dict:
        if self._stockout_units_by_quantity is None:
            self.simulate()
        return self._stockout_units_by_quantity

    @property
    def wasted_units_by_quantity(self) -> dict:
        if self._wasted_units_by_quantity is None:
            self.simulate()
        return self._wasted_units_by_quantity


class SimulationTypes(Enum):
    NON_PERISHABLE = ('NP', 'Fixed Term Perishable', NonPerishableInventorySimulator)

    def __init__(self, code, description, simulator):
        self._code = code
        self._description = description
        self._simulator = simulator

    @property
    def code(self):
        return self._code

    @property
    def description(self):
        return self._description

    @property
    def simulator(self):
        return self._simulator

    @staticmethod
    def get_simulator_by_code(code):
        for simulation_type in SimulationTypes:
            if simulation_type.code == code:
                return simulation_type.simulator
        raise ValueError(f"Simulation type {code} is not supported")


class SimulationsFactory:
    @staticmethod
    def get_simulator(product: Product, is_origin: bool):
        if len(product.lots_expiration_by_date) == 0:
            logger.info(f"Running simulation for non perishable product {product.sku}")
            return SimulationTypes.get_simulator_by_code('NP')(product, is_origin)
        raise ValueError("Simulation type not supported")


if __name__ == '__main__':
    # forecast_error_model = {'distribution': 'DISC', 'values': [0,1,3,4,4,5,5]}
    # forecast_error_model = {'distribution': 'NORM', 'mu': 10, 'sigma': 20.1}
    lead_time_model = {'distribution': 'WEIGHTED_DISCRETE', 'prob_value_pairs': {0: 0.1, 1: 0.2, 2: 0.3, 3: 0.4}}
    random_variates_generator = RandomVariates.get_distribution_by_code(
        lead_time_model.get('distribution', None)).generator(lead_time_model)
    forecast = 0
    sample_size = 5000
    random_variates = random_variates_generator.generate(forecast, sample_size)

    unique_supplier = Supplier(
        external_id="123",
        lead_time_model={
            'distribution': 'WEIGHTED_DISCRETE',
            'prob_value_pairs': {0: 0.1, 1: 0.2, 2: 0.3, 3: 0.4}
        },
        delay_model={0: 1}
    )

    origin_product = Product(
        sku="123",
        days_to_next_review=7,
        warehouse="VLP",
        current_inventory=4500,
        detailed_incoming_inventory={
            2030: {
                "2024-10-20": 10,
                "2021-11-22": 20,
                "2021-11-28": 30
            }
        },
        forecast={'2024-09-26': 128.0, '2024-09-27': 107.0, '2024-09-28': 56.0, '2024-09-29': 0.0, '2024-09-30': 119.0,
                  '2024-10-01': 111.0, '2024-10-02': 119.0, '2024-10-03': 103.0, '2024-10-04': 91.0, '2024-10-05': 89.0,
                  '2024-10-06': 0.0, '2024-10-07': 131.0, '2024-10-08': 111.0, '2024-10-09': 120.0,
                  '2024-10-10': 103.0},
        forecast_error_model={
            'distribution': 'NORM',
            'mu': 0.0,
            'sigma': 35
        },
        units_per_product_dim=50,
        desired_service_level=0.9,
        supplier_dim_to_product_dim_conversion_factor=20,
        current_price_per_unit=10,
        percentage_cost_per_unit_excess=100,
        percentage_cost_per_unit_shortage=15,
        mandatory=False,
        lots_expiration_by_date={},
        suppliers=[unique_supplier]
    )
    origin_product.add_supplier(unique_supplier)
    simulator = SimulationsFactory.get_simulator(origin_product, True)
    simulator.simulate(sample_size=10000)
    print(simulator.stockout_units_by_quantity)
    print(simulator.wasted_units_by_quantity)
