# coding:utf8

import os
import json
import numpy as np
import tensorflow as tf
tf.enable_eager_execution()
if tf.test.is_gpu_available():
    rnn = tf.keras.layers.CuDNNGRU
else:
    import functools
    rnn = functools.partial(tf.keras.layers.GRU, recurrent_activation='sigmoid')
from demo_backend.celery import app
from celery import shared_task

from .config import CHECKPOINTDIR, VOCABDIR
from .utils import remove_unwanted


with open(VOCABDIR, "r") as f:
    vocab = json.load(f)
vocab_size = len(vocab)
char2idx = {u:i for i, u in enumerate(vocab)}
idx2char = np.array(vocab)
embedding_dim = 256
rnn_units = 1024


def build_model(vocab_size, embedding_dim, rnn_units, batch_size):
    model = tf.keras.Sequential([
        tf.keras.layers.Embedding(vocab_size, embedding_dim, 
                              batch_input_shape=[batch_size, None]),
        rnn(rnn_units,
        return_sequences=True, 
        recurrent_initializer='glorot_uniform',
        stateful=True),
    tf.keras.layers.Dense(vocab_size)])
    return model


MODEL = build_model(vocab_size, embedding_dim, rnn_units, batch_size=1)
MODEL.load_weights(CHECKPOINTDIR)
MODEL.build(tf.TensorShape([1, None]))


@app.task(bind=True)
def generate_text(self, start_string):
    num_generate = 32
    input_eval = [char2idx[s] for s in start_string.split()]
    input_eval = tf.expand_dims(input_eval, 0)
    text_generated = []
    temperature = 1.0
    MODEL.reset_states()
    for i in range(num_generate):
        predictions = MODEL(input_eval)
        predictions = tf.squeeze(predictions, 0)
        predictions = predictions / temperature
        predicted_id = tf.multinomial(predictions, num_samples=1)[-1,0].numpy()
        input_eval = tf.expand_dims([predicted_id], 0)
        text_generated.append(idx2char[predicted_id])
    text = start_string + ''.join(text_generated)
    text = remove_unwanted(text)
    return text
