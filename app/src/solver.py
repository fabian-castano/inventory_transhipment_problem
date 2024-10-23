from app.src.classes import TranshipmentProblem, Product
from app.src.loggin import logger
from app.src.simulator import SimulationsFactory
import pulp as plp
from highsbox import highs_bin_path

BIG_M = 1000000


class Solver:
    def __init__(self, transhipment_problem: TranshipmentProblem):
        self.transhipment_problem = transhipment_problem
        self.model_products = {'origin': {}, 'destination': {}}
        self.valid_products = set()
        self._recommendations = {}

    def get_products_params(self):
        skip_list = []
        for _, product in self.transhipment_problem.origin_products.items():
            try:
                simulator = SimulationsFactory.get_simulator(product, is_origin=True)
                self.model_products['origin'][product.sku] = {
                    'lost_sales': simulator.stockout_units_by_quantity
                    , 'waste': simulator.wasted_units_by_quantity
                }
            except ValueError as e:
                logger.warning(f"Product {product.sku} was skipped because {str(e)}")
                skip_list.append(product.sku)
        for _, product in self.transhipment_problem.destination_products.items():
            if product.sku in skip_list:
                continue
            try:
                simulator = SimulationsFactory.get_simulator(product, is_origin=False)
                self.model_products['destination'][product.sku] = {
                    'lost_sales': simulator.stockout_units_by_quantity
                    , 'waste': simulator.wasted_units_by_quantity
                }
            except ValueError as e:
                logger.warning(f"Product {product.sku} was skipped because {str(e)}")

    def solve(self):
        self.get_products_params()
        self.set_valid_products()
        self.optimize()

    @property
    def recommendations(self):
        if len(self._recommendations) == 0:
            self.optimize()
        return self._recommendations

    def optimize(self):

        # enumerate sets
        products = list(set(self.valid_products))

        q_vals = {}
        for i in products:
            ori, des = len(self.model_products['origin'][i]['lost_sales'].keys()), len(
                self.model_products['destination'][i]['lost_sales'].keys())
            if ori <= des:
                q_vals[i] = list(self.model_products['origin'][i]['lost_sales'].keys())
            else:
                q_vals[i] = list(self.model_products['destination'][i]['lost_sales'].keys())

        valid_tuples = set([(i, j) for i in q_vals.keys() for j in q_vals[i]])

        warehouses = ['origin', 'destination']

        mandatory_products = [i for i in products if self.transhipment_problem.origin_products[i].mandatory]

        # enumerate problem parameters
        stockout_cost_per_unit = {
            self.transhipment_problem.origin_products[i].sku: self.transhipment_problem.origin_products[
                                                                  i].percentage_cost_per_unit_shortage / 100 *
                                                              self.transhipment_problem.origin_products[
                                                                  i].current_price_per_unit for i in products}
        waste_cost_per_unit = {
            self.transhipment_problem.origin_products[i].sku: self.transhipment_problem.origin_products[
                                                                  i].percentage_cost_per_unit_excess / 100 *
                                                              self.transhipment_problem.origin_products[
                                                                  i].current_price_per_unit for i in products}
        lot_size = {self.transhipment_problem.origin_products[i].sku: self.transhipment_problem.origin_products[
            i].units_per_product_dim for i in products}
        lots_per_pallet = {self.transhipment_problem.origin_products[i].sku: self.transhipment_problem.origin_products[
            i].supplier_dim_to_product_dim_conversion_factor for i in products}

        # create the model
        transhipment_model = plp.LpProblem("Transhipment", plp.LpMinimize)

        # declare the variables
        x = plp.LpVariable.dicts("transhipment", valid_tuples, lowBound=0, cat=plp.LpBinary)
        y = plp.LpVariable.dicts("transport_in_pallets", products, lowBound=0,
                                 cat=plp.LpBinary)  # takes the vaue 1 if the product is transhipped in closed pallets
        pallets = plp.LpVariable.dicts("pallets", products, lowBound=0, cat=plp.LpInteger)
        lots = plp.LpVariable.dicts("lots", products, lowBound=0, cat=plp.LpInteger)
        left_behind = plp.LpVariable.dicts("left_behind", products, lowBound=0, cat=plp.LpBinary)

        # objective function
        transhipment_model += plp.lpSum(
            [self.model_products['origin'][i]['lost_sales'][j] * stockout_cost_per_unit[i] * x[(i, j)] for i, j in
             valid_tuples]) + plp.lpSum(
            [self.model_products['origin'][i]['waste'][j] * waste_cost_per_unit[i] * x[(i, j)] for i, j in
             valid_tuples]) + BIG_M * plp.lpSum([left_behind[i] for i in products])

        # constraints

        # exactly one allocation per product
        for i in products:
            transhipment_model += plp.lpSum([x[(i, j)] for j in q_vals[i] if (i, j) in valid_tuples]) == 1, f"Exactly one allocation per product {i}"

        # mandatory products must be transhipped (at least one transfer unit)
        for i in mandatory_products:
            transhipment_model += plp.lpSum(
                [x[(i, j)] * j * 1 / lot_size[i] for j in q_vals[i] if (i, j) in valid_tuples]) >= 1 - left_behind[i], f"Mandatory product {i} must be transhipped"

        # pallets constraints
        for i in products:
            transhipment_model += plp.lpSum([x[(i, j)] * j * 1 / (lot_size[i] * lots_per_pallet[i]) for j in q_vals[i] if (i, j) in valid_tuples]) <= pallets[i] * lots_per_pallet[i] + BIG_M * (
                                              1 - y[i]), f"Respect the mandatory closed above pallets for product {i}"
            transhipment_model += plp.lpSum([x[(i, j)] * j * 1 / (lot_size[i] * lots_per_pallet[i]) for j in q_vals[i] if (i, j) in valid_tuples]) >= pallets[i] * lots_per_pallet[i] - BIG_M * (
                                              1 - y[i]), f"Respect the mandatory closed below pallets for product {i}"
            transhipment_model += plp.lpSum(
                [x[(i, j)] * j * 1 / (lot_size[i]) for j in q_vals[i] if (i, j) in valid_tuples]) <= lots[i] * lots_per_pallet[i] + BIG_M * (y[i]), f"Respect the mandatory closed above lots for product {i}"
            transhipment_model += plp.lpSum(
                [x[(i, j)] * j * 1 / (lot_size[i]) for j in q_vals[i] if (i, j) in valid_tuples]) >= lots[i] * lots_per_pallet[i] - BIG_M * (y[i]), f"Respect the mandatory closed below lots for product {i}"

        # respect the mandatory closed pallets
        transhipment_model += plp.lpSum(
            [pallets[i] for i in products]) >= self.transhipment_problem.mandatory_closed_transport_units, "Respect the mandatory closed pallets"

        # respect the capacity in transport units
        transhipment_model += plp.lpSum([x[(i, j)] * j * 1 / (lot_size[i] * lots_per_pallet[i]) for i, j in
                                         valid_tuples]) <= self.transhipment_problem.capacity_in_transport_units, "Respect the capacity in transport units"

        # solve the model
        transhipment_model.solve(plp.HiGHS_CMD(path=highs_bin_path()))

        if plp.LpStatus[transhipment_model.status] == 'Optimal':

            if sum([left_behind[i].varValue for i in products]) > 0:
                logger.warning("Some mandatory products could not be transshipped")

            for i, j in valid_tuples:
                if x[(i, j)].varValue == 1:
                    self.recommendations[i] = j
        else:
            raise ValueError("The model could not be solved")

    def set_valid_products(self):
        # the valid products are those that are both in origin and destination and have quantities to transfer from origin to destination larger than 0
        _products = set(self.model_products['origin'].keys()) & set(self.model_products['destination'].keys())
        for product in _products:
            if len(self.model_products['origin'][product]['lost_sales'].keys()) > 0:
                self.valid_products.add(product)

    def get_recommendations(self):
        return self.recommendations
