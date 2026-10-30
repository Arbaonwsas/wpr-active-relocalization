"""Run the existing benchmark against the isolated AMCL experiment."""
import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    'benchmark',
    str(Path(__file__).resolve().parents[3] / 'scripts/benchmark_global_relocalization.py'),
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)
benchmark.TEST_POSES = (('isolated_ambiguous_room', -3.5, 1.93, -2.52),)
original_capture = benchmark.capture_topic


def isolated_capture(topic, field=None, timeout=10):
    if topic == '/amcl_pose':
        topic = '/isolated_amcl_pose'
    return original_capture(topic, field=field, timeout=timeout)


benchmark.capture_topic = isolated_capture
if __name__ == '__main__':
    benchmark.main()
