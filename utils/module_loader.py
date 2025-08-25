import os
import copy
import pytorch_lightning as pl
import datetime
import wandb

from pytorch_lightning.loggers import WandbLogger
from data.toolset import ToolSet
from model.model_interface import ModelInterface
from data.dataset.dataset_interface import DataInterface
from pytorch_lightning.strategies import DDPStrategy

import os
import copy
import pytorch_lightning as pl
import datetime
import wandb

from pytorch_lightning.loggers import WandbLogger, TensorBoardLogger
from model.model_interface import ModelInterface
from data.dataset.dataset_interface import DataInterface
from pytorch_lightning.strategies import DDPStrategy, DeepSpeedStrategy, Strategy

from model.tool_selector.retriever_selector import RetrieverSelector


################################################################################
################################ load model ####################################
################################################################################
def my_load_model(config):
    model_config = copy.deepcopy(config)
    model_type = model_config.pop("model_py_path")

    if "kwargs" in model_config.keys():
        kwargs = model_config.pop("kwargs")
    else:
        kwargs = {}

    model_config.update(kwargs)

    if model_type == "saprot_classification_model":
        from agent.tools.saprot_task.saprot.saprot_classification_model import SaprotClassificationModel
        return SaprotClassificationModel(**model_config)

    if model_type == "saprot_token_classification_model":
        from agent.tools.saprot_task.saprot.saprot_token_classification_model import (
            SaprotTokenClassificationModel,
        )

        return SaprotTokenClassificationModel(**model_config)

    if model_type == "saprot_regression_model":
        if "num_labels" in model_config:
            del model_config["num_labels"]
        from agent.tools.saprot_task.saprot.saprot_regression_model import SaprotRegressionModel

        return SaprotRegressionModel(**model_config)

    if model_type == "saprot_pair_classification_model":
        from agent.tools.saprot_task.saprot.saprot_pair_classification_model import (
            SaprotPairClassificationModel,
        )

        return SaprotPairClassificationModel(**model_config)

    if model_type == "saprot_pair_regression_model":
        from agent.tools.saprot_task.saprot.saprot_pair_regression_model import SaprotPairRegressionModel

        return SaprotPairRegressionModel(**model_config)


################################################################################
################################ load dataset ##################################
################################################################################
def my_load_dataset(config):
    dataset_config = copy.deepcopy(config)
    dataset_type = dataset_config.pop("dataset_py_path")
    kwargs = dataset_config.pop("kwargs")
    dataset_config.update(kwargs)

    if dataset_type == "saprot/saprot_classification_dataset":
        from data.dataset.saprot.saprot_classification_dataset import (
            SaprotClassificationDataset,
        )

        return SaprotClassificationDataset(**dataset_config)

    if dataset_type == "saprot/saprot_token_classification_dataset":
        if "plddt_threshold" in dataset_config:
            del dataset_config["plddt_threshold"]
        from data.dataset.saprot.saprot_token_classification_dataset import (
            SaprotTokenClassificationDataset,
        )

        return SaprotTokenClassificationDataset(**dataset_config)

    if dataset_type == "saprot/saprot_regression_dataset":
        from data.dataset.saprot.saprot_regression_dataset import SaprotRegressionDataset

        return SaprotRegressionDataset(**dataset_config)

    if dataset_type == "saprot/saprot_pair_classification_dataset":
        from data.dataset.saprot.saprot_pair_classification_dataset import (
            SaprotPairClassificationDataset,
        )

        return SaprotPairClassificationDataset(**dataset_config)

    if dataset_type == "saprot/saprot_pair_regression_dataset":
        from data.dataset.saprot.saprot_pair_regression_dataset import (
            SaprotPairRegressionDataset,
        )

        return SaprotPairRegressionDataset(**dataset_config)


def load_wandb(config):
    # initialize wandb
    wandb_config = config.setting.wandb_config
    wandb_logger = WandbLogger(
        project=wandb_config.project,
        config=config,
        name=wandb_config.name,
        settings=wandb.Settings(),
    )

    return wandb_logger


def load_model(config):
    # initialize model
    model_config = copy.deepcopy(config)

    if "kwargs" in model_config.keys():
        kwargs = model_config.pop("kwargs")
    else:
        kwargs = {}

    model_config.update(kwargs)
    return ModelInterface.init_model(**model_config)


def load_dataset(config):
    # initialize dataset
    dataset_config = copy.deepcopy(config)

    if "kwargs" in dataset_config.keys():
        kwargs = dataset_config.pop("kwargs")
    else:
        kwargs = {}

    dataset_config.update(kwargs)
    return DataInterface.init_dataset(**dataset_config)


# Initialize strategy
def load_strategy(config):
    config = copy.deepcopy(config)
    if "timeout" in config.keys():
        timeout = int(config.pop("timeout"))
        config["timeout"] = datetime.timedelta(seconds=timeout)

    cls = config.pop("class")
    return eval(cls)(**config)


# Initialize a pytorch lightning trainer
def load_trainer(config):
    trainer_config = copy.deepcopy(config.Trainer)

    trainer_config.pop("strategy")

    return pl.Trainer(**trainer_config, callbacks=[], use_distributed_sampler=False)


def load_toolset(config):
    # initialize toolset
    toolset_config = copy.deepcopy(config)
    kwargs = toolset_config.pop("kwargs")
    toolset_config.update(kwargs)
    return ToolSet(**toolset_config)


def load_selector(config, toolset):
    # initialize model
    selector_config = copy.deepcopy(config)
    kwargs = selector_config.pop("kwargs")
    selector_config.update(kwargs)
    selector_config.toolset = toolset
    # return ModelInterface.init_model(**selector_config)
    return RetrieverSelector(**selector_config)
