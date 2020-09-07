# Copyright 2020 The AutoKeras Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os

import official.nlp.bert.bert_models
import official.nlp.bert.configs
import tensorflow as tf

GS_FOLDER_BERT = "gs://cloud-tpu-checkpoints/bert/keras_bert/uncased_L-12_H-768_A-12"
HUB_URL_BERT = "https://tfhub.dev/tensorflow/bert_en_uncased_L-12_H-768_A-12/2"


def BERT():
    bert_config_file = os.path.join(GS_FOLDER_BERT, "bert_config.json")
    config_dict = json.loads(tf.io.gfile.GFile(bert_config_file).read())

    bert_config = official.nlp.bert.configs.BertConfig.from_dict(config_dict)

    bert_classifier, bert_encoder = official.nlp.bert.bert_models.classifier_model(
        bert_config, num_labels=2
    )

    checkpoint = tf.train.Checkpoint(model=bert_encoder)

    checkpoint.restore(
        os.path.join(GS_FOLDER_BERT, "bert_model.ckpt")
    ).assert_consumed()

    return bert_encoder