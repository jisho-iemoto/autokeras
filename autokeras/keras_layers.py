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

import numpy as np
import tensorflow as tf
from tensorflow.keras.layers.experimental import preprocessing
from tensorflow.python.util import nest

INT = "int"
NONE = "none"
ONE_HOT = "one-hot"


@tf.keras.utils.register_keras_serializable()
class MultiCategoryEncoding(preprocessing.PreprocessingLayer):
    """Encode the categorical features to numerical features.

    # Arguments
        encoding: A list of strings, which has the same number of elements as the
            columns in the structured data. Each of the strings specifies the
            encoding method used for the corresponding column. Use 'int' for
            categorical columns and 'none' for numerical columns.
    """

    # TODO: Support one-hot encoding.
    # TODO: Support frequency encoding.

    def __init__(self, encoding, **kwargs):
        super().__init__(**kwargs)
        self.encoding = encoding
        self.encoding_layers = []
        for encoding in self.encoding:
            if encoding == NONE:
                self.encoding_layers.append(None)
            elif encoding == INT:
                self.encoding_layers.append(preprocessing.StringLookup())
            elif encoding == ONE_HOT:
                self.encoding_layers.append(None)

    def build(self, input_shape):
        for encoding_layer in self.encoding_layers:
            if encoding_layer is not None:
                encoding_layer.build(tf.TensorShape([1]))

    def call(self, inputs):
        input_nodes = nest.flatten(inputs)[0]
        split_inputs = tf.split(input_nodes, [1] * len(self.encoding), axis=-1)
        output_nodes = []
        for input_node, encoding_layer in zip(split_inputs, self.encoding_layers):
            if encoding_layer is None:
                number = tf.strings.to_number(input_node, tf.float32)
                # Replace NaN with 0.
                imputed = tf.where(
                    tf.math.is_nan(number), tf.zeros_like(number), number
                )
                output_nodes.append(imputed)
            else:
                output_nodes.append(tf.cast(encoding_layer(input_node), tf.float32))
        if len(output_nodes) == 1:
            return output_nodes[0]
        return tf.keras.layers.Concatenate()(output_nodes)

    def adapt(self, data):
        for index, encoding_layer in enumerate(self.encoding_layers):
            if encoding_layer is None:
                continue
            data_column = data.map(lambda x: tf.slice(x, [0, index], [-1, 1]))
            encoding_layer.adapt(data_column)

    def get_config(self):
        config = {
            "encoding": self.encoding,
        }
        base_config = super().get_config()
        return dict(list(base_config.items()) + list(config.items()))


class TextVectorizationWithTokenizer(preprocessing.PreprocessingLayer):
    """Vectorization and Encoding the sentences using a given Tokenizer

    # Arguments
        tokenizer : bert.tokenization.FullTokenizer(
            vocab_file=os.path.join(gs_folder_bert, "vocab.txt"),
            do_lower_case=True)
        max_seq_len : maximum length of the sequences after vectorization.
    """

    def __init__(self, tokenizer, max_seq_len):
        super().__init__()
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len

    def build(self, input_shape):
        self.batch_size = input_shape

    def call(self, inputs):
        output = tf.numpy_function(
            func=self.bert_encode, inp=[inputs], Tout=tf.int32
        )
        output.set_shape((None, None, None))
        return output

    def encode_sentence(self, s):
        """Encodes a sentence using the BERT tokenizer.

        Tokenizes, and adjusts the sentence length to the maximum sequence
        length. Some important tokens in the BERT tokenizer are:
        [UNK]: 100
        [CLS]: 101
        [SEP]: 102
        [MASK]: 103
        Arguments:
            s : Raw sentence string.
        """
        tokens = list(self.tokenizer.tokenize(s))
        tokens.append("[SEP]")
        if len(tokens) < self.max_seq_len - 1:
            tokens = tokens + ["[UNK]"] * (self.max_seq_len - len(tokens) - 1)
        else:
            tokens = tokens[0 : self.max_seq_len - 1]
        encoded_sentence = self.tokenizer.convert_tokens_to_ids(tokens)
        return encoded_sentence

    def get_encoded_sentence(self, input_tensor):
        input_array = np.array(input_tensor, dtype=object)
        sentence = tf.constant([self.encode_sentence(s[0]) for s in input_array])
        return sentence

    def bert_encode(self, input_tensor):
        sentence = self.get_encoded_sentence(input_tensor)
        cls = [self.tokenizer.convert_tokens_to_ids(["[CLS]"])] * sentence.shape[0]
        input_word_ids = tf.concat([cls, sentence], axis=-1)
        input_mask = tf.ones_like(input_word_ids).numpy()
        type_cls = tf.zeros_like(cls)
        type_s1 = tf.zeros_like(sentence)
        input_type_ids = tf.concat([type_cls, type_s1], axis=-1).numpy()
        inputs = tf.stack([input_word_ids.numpy(), input_mask, input_type_ids])
        return inputs
