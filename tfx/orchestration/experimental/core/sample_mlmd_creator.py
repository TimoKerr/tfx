# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Creates testing MLMD with TFX data model."""
import os

from absl import app
from absl import flags

from tfx.orchestration import metadata
from tfx.orchestration.experimental.core import pipeline_ops
from tfx.orchestration.experimental.core import test_utils
from tfx.orchestration.portable import runtime_parameter_utils
from tfx.proto.orchestration import pipeline_pb2
from tfx.utils import io_utils

from ml_metadata.proto import metadata_store_pb2

FLAGS = flags.FLAGS

flags.DEFINE_string('path', '', 'path of mlmd database file')
flags.DEFINE_string('ir_dir', '', 'directory path of output IR files')
flags.DEFINE_integer('pipeline_run_num', 5, 'number of pipeline run')
flags.DEFINE_string('pipeline_id', 'uci-sample-generated', 'id of pipeline')


def _get_mlmd_connection(path: str) -> metadata.Metadata:
  """Returns a MetadataStore for performing MLMD API calls."""
  if os.path.isfile(path):
    raise IOError('File already exists: %s' % path)
  connection_config = metadata.sqlite_metadata_connection_config(path)
  connection_config.sqlite.SetInParent()
  return metadata.Metadata(connection_config=connection_config)


def _test_pipeline(pipeline_id: str, run_id: str):
  """Creates test pipeline with pipeline_id and run_id."""
  pipeline = pipeline_pb2.Pipeline()
  path = os.path.join(
      os.path.dirname(__file__), 'testdata', 'sync_pipeline.pbtxt')
  io_utils.parse_pbtxt_file(path, pipeline)
  pipeline.pipeline_info.id = pipeline_id
  runtime_parameter_utils.substitute_runtime_parameter(pipeline, {
      'pipeline_run_id': run_id,
  })
  return pipeline


def _execute_nodes(handle: metadata.Metadata, pipeline: pipeline_pb2.Pipeline,
                   version: int):
  """Creates fake execution of nodes."""
  example_gen = test_utils.get_node(pipeline, 'my_example_gen')
  stats_gen = test_utils.get_node(pipeline, 'my_statistics_gen')
  schema_gen = test_utils.get_node(pipeline, 'my_schema_gen')
  transform = test_utils.get_node(pipeline, 'my_transform')
  example_validator = test_utils.get_node(pipeline, 'my_example_validator')
  trainer = test_utils.get_node(pipeline, 'my_trainer')

  test_utils.fake_example_gen_run_with_handle(handle, example_gen, 1, version)
  test_utils.fake_component_output_with_handle(handle, stats_gen, active=False)
  test_utils.fake_component_output_with_handle(handle, schema_gen, active=False)
  test_utils.fake_component_output_with_handle(handle, transform, active=False)
  test_utils.fake_component_output_with_handle(
      handle, example_validator, active=False)
  test_utils.fake_component_output_with_handle(handle, trainer, active=False)


def create_sample_pipeline(m: metadata.Metadata,
                           pipeline_id: str,
                           run_num: int,
                           export_ir_path: str = ''):
  """Creates a list of pipeline and node execution."""
  for i in range(run_num):
    run_id = 'run%02d' % i
    pipeline = _test_pipeline(pipeline_id, run_id)
    if export_ir_path:
      output_path = os.path.join(export_ir_path,
                                 '%s_%s.pbtxt' % (pipeline_id, run_id))
      io_utils.write_pbtxt_file(output_path, pipeline)
    pipeline_state = pipeline_ops.initiate_pipeline_start(m, pipeline)
    _execute_nodes(m, pipeline, i)
    if i < run_num - 1:
      with pipeline_state:
        pipeline_state.set_pipeline_execution_state(
            metadata_store_pb2.Execution.COMPLETE)


def main_factory(mlmd_connection_func):

  def main(argv):
    del argv
    with mlmd_connection_func(FLAGS.path) as m:
      create_sample_pipeline(m, FLAGS.pipeline_id, FLAGS.pipeline_run_num,
                             FLAGS.ir_dir)

  return main


if __name__ == '__main__':
  app.run(main_factory(_get_mlmd_connection))
