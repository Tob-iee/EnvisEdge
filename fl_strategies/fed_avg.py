import logging
from typing import Dict

import numpy as np
from fedrec.python_executors.aggregator import Neighbour
from fedrec.user_modules.envis_base_module import EnvisBase
from fedrec.user_modules.envis_preprocessor import EnvisPreProcessor
from fedrec.utilities import registry
from fedrec.utilities.random_state import RandomContext


@registry.load('aggregator', 'fed_avg')
class FedAvg(EnvisBase):
    def __init__(self,
                 config_dict: Dict,
                 in_neighbours: Dict[int, Neighbour] = None,
                 out_neighbours: Dict[int, Neighbour] = None):
        super().__init__(config_dict["random"])
        self.in_neighbours = in_neighbours
        self.out_neighbours = out_neighbours
        self.config_dict = config_dict
        modelCls = registry.lookup('model', self.config_dict["model"])
        self.model_preproc: EnvisPreProcessor = registry.instantiate(
            modelCls.Preproc,
            self.config_dict["model"]['preproc'])
        self._model = None

    @property
    def model(self):
        if self._model is not None:
            return self._model

        with self.model_random:
            # 1. Construct model
            self.model_preproc.load_data_description()
            self._model = registry.construct(
                'model', self.config_dict["model"],
                preprocessor=self.model_preproc,
                unused_keys=('name', 'preproc')
            )
        return self._model

    def aggregate(self):
        model_list = [None] * len(self.in_neighbours.values())
        training_num = 0

        for idx, neighbour in enumerate(self.in_neighbours.values()):
            model_list[idx] = (neighbour.sample_num, neighbour.model)
            training_num += neighbour.sample_num

        (sample_num0, averaged_params) = model_list[0]
        for k in averaged_params.keys():
            averaged_params[k] *= sample_num0/training_num
            for sample_num, params in model_list:
                averaged_params[k] += params[k] * (sample_num/training_num)

        return averaged_params

    def sample_clients(self, round_idx, client_num_per_round):
        num_neighbours = len(self.in_neighbours)
        if num_neighbours == client_num_per_round:
            selected_neighbours = [
                neighbour for neighbour in self.in_neighbours]
        else:
            with RandomContext(round_idx):
                selected_neighbours = np.random.choice(
                    self.in_neighbours,
                    min(client_num_per_round, num_neighbours),
                    replace=False)
        logging.info("worker_indexes = %s" % str(selected_neighbours))
        return selected_neighbours
