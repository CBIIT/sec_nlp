# %%
!curl -L https://huggingface.co/ChrisLiewJY/BERTweet-Hedge/resolve/main/training_args.bin -O

# %%
import torch
from transformers import Trainer, TrainingArguments, IntervalStrategy, SchedulerType
from transformers.training_args import OptimizerNames
from transformers.trainer_utils import HubStrategy

# Specify the path to the training_args.bin file
path_to_training_args = "training_args.bin"
torch.serialization.add_safe_globals(
    [TrainingArguments, IntervalStrategy, SchedulerType, OptimizerNames, HubStrategy]
)

# Load the training arguments using torch.load()
training_args = torch.load(path_to_training_args, weights_only=True)
# Manually add the missing attribute if it doesn't exist
if not hasattr(training_args, 'lr_scheduler_kwargs'):
    training_args.lr_scheduler_kwargs = {}

training_args

# %%
