# Copyright 2021 Google LLC. All Rights Reserved.
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
"""TFX Conditionals."""
import collections
import threading
from typing import FrozenSet

from tfx.dsl.components.base import base_node
from tfx.dsl.components.base import node_registry
from tfx.dsl.experimental.conditionals import predicate as predicate_lib


class _ConditionalRegistry(threading.local):
  """Registers the predicates that a node is associated with in local thread."""

  def __init__(self):
    super().__init__()
    self.node_frames = dict()
    self.conditional_map = collections.defaultdict(set)

  def enter_conditional(self, predicate: predicate_lib.Predicate):
    self.node_frames[predicate] = node_registry.registered_nodes()

  def exit_conditional(self, predicate: predicate_lib.Predicate):
    nodes_in_frame = (
        node_registry.registered_nodes() - self.node_frames[predicate])
    for node in nodes_in_frame:
      self.conditional_map[node].add(predicate)

_conditional_registry = _ConditionalRegistry()


def get_predicates(
    node: base_node.BaseNode) -> FrozenSet[predicate_lib.Predicate]:
  """Get predicates that a node is associated with in local thread."""
  return frozenset(_conditional_registry.conditional_map[node])


class Cond:
  """Context manager that registers a predicate with nodes in local thread."""

  def __init__(self, predicate: predicate_lib.Predicate):
    self._predicate = predicate

  def __enter__(self):
    _conditional_registry.enter_conditional(self._predicate)

  def __exit__(self, exc_type, exc_val, exc_tb):
    _conditional_registry.exit_conditional(self._predicate)
