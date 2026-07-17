"""Candidate-owned model architecture."""

import torch


class Model(torch.nn.Module):
    def __init__(self, input_size, output_size, device):
        super().__init__()
        self.network = torch.nn.Linear(input_size, output_size, device=device)

    def forward(self, inputs):
        return self.network(inputs)
