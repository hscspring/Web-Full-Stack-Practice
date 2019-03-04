# coding: utf8

import os
from django.conf import settings

checkpoint_dir = os.path.join(os.path.dirname(__file__), "training_checkpoints", "ckpt_50")
vocab_dir = os.path.join(os.path.dirname(__file__), "training_checkpoints", "vocab")
# 如果项目的 setting 中没有指定，就根据这里的，项目中的会覆盖掉 APP 的配置
CHECKPOINTDIR = settings.TFMODEL_CHECKPOINTDIR if hasattr(settings, 'TFMODEL_CHECKPOINTDIR') else checkpoint_dir
VOCABDIR = settings.TFMODEL_VOCABDIR if hasattr(settings, 'TFMODEL_VOCABDIR') else vocab_dir