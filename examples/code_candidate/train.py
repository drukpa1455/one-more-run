"""Candidate-owned training algorithm."""

import torch

from features import transform
from model import Model


def train(inputs, targets, validation_inputs):
    training_features = transform(inputs)
    validation_features = transform(validation_inputs)
    model = Model(training_features.shape[1], targets.shape[1], inputs.device)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
    for _ in range(100):
        optimizer.zero_grad()
        loss = torch.mean((model(training_features) - targets) ** 2)
        loss.backward()
        optimizer.step()
    return model(validation_features)
