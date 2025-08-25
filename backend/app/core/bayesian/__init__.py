"""
Модуль байесовских методов для анализа лотерей
Включает CDM (Compound Dirichlet-Multinomial) модель
"""

from .dirichlet_model import DirichletMultinomialModel
from .prior_posterior import PriorPosteriorManager
from .bayesian_updater import BayesianUpdater
from .cdm_generator import CDMGenerator

__all__ = [
    'DirichletMultinomialModel',
    'PriorPosteriorManager',
    'BayesianUpdater',
    'CDMGenerator'
]