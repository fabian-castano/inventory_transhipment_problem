import json
import os
from app.src.loggin import logger
from app.src.classes import TranshipmentProblem, Product, Supplier
from app.src.solver import Solver


def run(event: dict):
    """
    :param event: dict with the information required to run the solver step

    """
    logger.info("Running solver step")
    # Load the transhipment problem
    absolute_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # /data/process/inputs/
    path_to_process_inputs = os.path.join(absolute_path, 'data', 'process', 'inputs')

    with open(os.path.join(path_to_process_inputs, 'transhipment_problem_payload.json')) as f:
        data = json.load(f)

    logger.info(data)
    lista_productos = data['origin_products']
    for products in  lista_productos:
        #products['lots_expiration_by_date'] = {}
        products['suppliers'] = [Supplier(**supplier) for supplier in products['suppliers'] ]


    lista_productos = data['destination_products']
    for products in  lista_productos:
        #products['lots_expiration_by_date'] = {}
        products['suppliers'] = [Supplier(**supplier) for supplier in products['suppliers'] ]



    problem = TranshipmentProblem(
        execution_id=data['execution_id'],
        origin_warehouse=data['origin_warehouse'],
        destination_warehouse=data['destination_warehouse'],
        execution_date=data['execution_date'],
        transhipment_lead_time_probability=data['transhipment_lead_time'],
        mandatory_closed_transport_units=data['mandatory_closed_transport_units'],
        capacity_in_transport_units=data['capacity_in_transport_units'],
        origin_products={product['sku']: Product(**product) for product in data['origin_products'] },
        destination_products={product['sku']: Product(**product) for product in data['destination_products']}
    )

    logger.info(problem._to_dict())

    solver = Solver(problem)
    solver.solve()

    result = solver.recommendations


if __name__ == '__main__':
    run({})