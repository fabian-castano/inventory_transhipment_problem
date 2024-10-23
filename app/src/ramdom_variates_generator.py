from app.src.classes import Product
from datetime import datetime, timedelta
import numpy as np
# random truncted normal distribution
import scipy.stats
import statsmodels.api as sm
from abc import ABC, abstractmethod
from app.src.loggin import logger
from enum import Enum


class RandomVariatesGenerator(ABC):
    def __init__(self, forecast_error_model):
        self.forecast_error_model = forecast_error_model
        self.validate_error_model()

    def validate_error_model(self):
        dist = RandomVariates.get_distribution_by_code(self.forecast_error_model.get('distribution', None))
        if dist is None:
            raise ValueError("None is not a valid distribution")
        for param in dist.params['params']:
            if param not in self.forecast_error_model:
                raise ValueError(f"Parameter {param} is missing in the location error model")

    @abstractmethod
    def generate(self, location: float, sample_size: int = 1):
        pass


class TruncatedNormalRandomVariatesGenerator(RandomVariatesGenerator):
    def __init__(self, forecast_error_model):
        super().__init__(forecast_error_model)
        if self.forecast_error_model.get('distribution', None) != 'NORM':
            raise ValueError("The demand location error distribution is not normal")

        self.mu = 0  # TODO: revise whether a different value is desired self.forecast_error_model.get('mu', 0)
        self.sigma = self.forecast_error_model.get('sigma', 0.0001)
        self.min_value = 0
        self.max_value = np.inf

    def generate(self, forecast: float, sample_size: int = 1):
        # TODO: remove this hack
        _sigma=self.sigma
        if _sigma <= 0:
            _sigma=0.0001
        return np.round(scipy.stats.truncnorm.rvs((self.min_value - (forecast + self.mu)) / _sigma,
                                                  (self.max_value - (forecast + self.mu)) / _sigma,
                                                  loc=(forecast + self.mu), scale=_sigma, size=sample_size), 0)


class DiscreteRandomVariatesGenerator(RandomVariatesGenerator):

    def __init__(self, forecast_error_model):
        super().__init__(forecast_error_model)
        self._kde = None

    def construct_kde(self,
                      location: float
                      ):
        if self.forecast_error_model.get('distribution', None) != 'DISC':
            raise ValueError("The demand location error distribution is not discrete")

        forecast_error = self.forecast_error_model.get('values', [0])

        fcst = [location - i for i in forecast_error]
        fcst = [i for i in fcst]
        fcst = [i for i in fcst if i >= 0]

        if len(fcst) == 0:
            fcst = [location]
        if np.std(fcst) == 0 or len(fcst) == 0:
            logger.warning("Not enough data to construct the KDE")
            self._kde = self.probability_of_each_value_in_list([int(i) for i in fcst])
        else:
            dens = sm.nonparametric.KDEUnivariate(fcst)
            dens.fit(bw='scott', kernel='gau')
            self._kde = self.probability_of_each_value_in_list([int(i) for i in list(dens.icdf)])

    @staticmethod
    def probability_of_each_value_in_list(list_values: list):
        """
        Computes the probability of each value in the list
        :param list_values:
        :return:
        """
        # logger.info("Computing probability of each value in the list")
        total = len(list_values)
        dict_prob = {}
        for i in list_values:
            dict_prob[i] = list_values.count(i) / total
        return dict_prob

    def generate(self, forecast: float, sample_size: int = 1):
        self.construct_kde(forecast)
        vals = list(self._kde.keys())
        weights = [self._kde[v] for v in vals]
        return np.random.choice(vals, sample_size, p=weights)


class WeightedDiscreteRandomVariatesGenerator(RandomVariatesGenerator):
    def __init__(self, forecast_error_model):
        super().__init__(forecast_error_model)
        self._prob_value_pairs = None

    def generate(self, location: float, sample_size: int = 1):
        self._prob_value_pairs = self.forecast_error_model.get('prob_value_pairs', None)
        try:
            self._prob_value_pairs ={float(k):v for k,v in self._prob_value_pairs.items()}
        except:
            raise ValueError("The keys of the demand location error distribution must be numeric")
        if self._prob_value_pairs is None:
            raise ValueError("The demand location error distribution is not discrete")
        vals = np.array([float(v) for v in self._prob_value_pairs.keys()])
        weights = [self._prob_value_pairs[v] for v in vals]
        return np.random.choice(vals+location, sample_size, p=weights)


class RandomVariates(Enum):
    NORM = ('NORM', {'params': ['mu', 'sigma']}, TruncatedNormalRandomVariatesGenerator)
    DISC = ('DISC', {'params': ['values']}, DiscreteRandomVariatesGenerator)
    WEIGHTED_DISCRETE = ('WEIGHTED_DISCRETE', {'params': ['prob_value_pairs']}, WeightedDiscreteRandomVariatesGenerator)
    """
    EXPONENTIAL = ('EXPONENTIAL', {'params': ['lambda']})
    GAMMA = ('GAMMA', {'params': ['alpha', 'beta']})
    BETA = ('BETA', {'params': ['alpha', 'beta']})"""

    def __init__(self, code, params, generator):
        self._code = code
        self._params = params
        self._generator = generator

    @property
    def code(self):
        return self._code

    @property
    def params(self):
        return self._params

    @property
    def generator(self):
        return self._generator

    @staticmethod
    def get_distribution_by_code(code):
        for distribution in RandomVariates:
            if distribution.code == code:
                return distribution
        raise ValueError(f"Distribution {code} is not supported")


if __name__ == '__main__':
    # forecast_error_model = {'distribution': 'DISC', 'values': [0,1,3,4,4,5,5]}
    # forecast_error_model = {'distribution': 'NORM', 'mu': 10, 'sigma': 20.1}
    lead_time_model = {'distribution': 'WEIGHTED_DISCRETE', 'prob_value_pairs': {0: 0.1, 1: 0.2, 2: 0.3, 3: 0.4}}
    random_variates_generator = RandomVariates.get_distribution_by_code(
        lead_time_model.get('distribution', None)).generator(lead_time_model)
    forecast = 100
    sample_size = 10000
    random_variates = random_variates_generator.generate(forecast, sample_size)
    print(random_variates,np.mean(random_variates),np.std(random_variates))
