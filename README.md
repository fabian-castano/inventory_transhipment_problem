# analytics_inventory-transfers-model

This project aims at creating a framework for optimizing the inventory transfers between warehouses.
The goal is to minimize the cost of stockouts and spoilage while respecting the service levels and the
transportation capacity constraints.

The framework is structured as follows:

- **Data gathering**: The data is collected from the different datasources using endpoints and stored in a json file that constitutes a payload for the subsequent steps.
- **Data processing**: The data is processed to extract the relevant information and to create the necessary features for the optimization model. This is achieved through a Montecarlo simulation that serves as a proxy to estimate the impact of either retiring or receiving **Q** units from a warehouse **i** to a warehouse **j**.
- **Optimization model**: The optimization model is a mixed-integer linear programming model that aims at minimizing the cost of stockouts and spoilage while respecting the service levels and the transportation capacity (and other custom) constraints.
- **Results**: The results are stored in a csv file that contains the best transfers and is available via MLops data serving.

# BATATAtrix Reloaded

## Objetivo

Batata es un modelo orientado a determinar una manera costo eficiencia de reubicar el inventario existente entre las difers bodegas con el objetivo de evitar stockouts y ayudar a controlar la merma cuando sea posible. También permite determinar la manera de movilizar el inventario entre las bodegas cuando todas las compras se realizan desde una única ubicación.

## Modelo

### Conjuntos

* $I$ conjunto de productos
* $Q_i$ cantidades preprocesadas a movilizar del producto $i$ entre el orígen y el destino ($Q_i\leftarrow \{q_i^1, q_i^2, \ldots, q_i^{|Q_i|}\}$)
* $W$ conjunto de bodegas $[origin,destination]$
* $O \subseteq I$ conjunto de productos que se deben mover entre las bodegas (e.g. superbodegas)

### Parámetros

* $S_{i\omega}(q_i)$: Valor esperado de stockout para el producto $i$ en la bodega $\omega$ cuando se movilizan $q_i$ unidades entre el orígen y el destino
* $W_{i\omega}(q_i)$: Valor esperado de unidades mermadas por exceso de stock para el producto $i$ en la bodega $\omega$ cuando se movilizan $q_i$ unidades
* $u_i$ : unidad de transferencia mínima para el producto $i$
* $f_i$ : número de unidades de transferencia mínima que caben en una *unidad de transporte* (pallet) para el producto $i$
* $l_i$ : costo de perder una venta por cada unidad de producto $i$ (e.g. margen*precio de compra)
* $\beta_i$ : costo de mermar una unidad de producto $i$ (e.g. precio de compra)
* $T$ : número de unidades de transporte disponibles (pallets)
* $E$: cantidad de pallets que deben ser movilizados con un único producto ($quebrados = T-E$)

### Variables de decisión

* $x_{iq_{i}^j}$: Variable binaria que indica si se movilizan $q_i^j$ unidades del producto $i$ entre las bodegas
* $N_i$ : número de unidades de transporte enteras que se movilizan del producto $i$
* $p_i$: número de unidades de transferencia mínima que se movilizan del producto $i$ en el pallet
* $y_i$ : variable binaria que toma el valor de 0 si se movilizan pallets con unidades de transferencia mínima (pallets quebrados) del producto $i$ o 1 si se movilizan unidades de transporte enteras del producto $i$


### Modelo

**Objetivo:**

Minimizar el costo total de ventas perdidas y merma asociado a la movilización de inventario entre las bodegas.

$\min \sum_{i \in I} \sum_{\omega \in W} \sum_{j \in Q_i} S_{i\omega}(q_i^j) \cdot x_{iq_{i}^j} \cdot l_i + \sum_{i \in I} \sum_{\omega \in W} \sum_{j \in Q_i} W_{i\omega}(q_i^j) \cdot x_{iq_{i}^j} \cdot \beta_i$

**Sujeto a:**

* solo se asocia una cantidad a transferir entre el orígen y el destino.
> $\sum_{j \in Q_i} x_{iq_{i}^j} =1 \qquad \forall i \in I$

* se moviliza al menos una unidad de transferencia obligatoria del producto $i$ entre el orígen y el destino.
> $\sum_{j \in Q_i}\frac{ q_i^j \cdot x_{iq_{i}^j}}{u_i} \geq n_i \qquad \forall i \in O$

* restricción auxiliar para determinar si un producto se moviliza en pallets completos o en pallets quebrados (agrego una tolerancia al cero para lidiar con problemas numéricos potenciales $\epsilon$).
> $N_i - Big\_M*(1-y_i) -\epsilon \leq \sum_{j \in Q_i}\frac{ q_i^j \cdot x_{iq_{i}^j}}{u_i\cdot f_i} \leq N_i + Big\_M*(1-y_i)+\epsilon \qquad \forall i \in I$  

* No se debe sobre pasar la capacidad de transporte disponible (medida en unidades de transporte)

 $\sum_{i \in I}\sum_{j \in Q_i}\frac{ q_i^j \cdot x_{iq_{i}^j}}{u_if_i} \leq T$

* Se debe movilizar la cantidad de unidades de transporte enteras que se requiere.
> $\sum_{i \in I} N_i \geq E$