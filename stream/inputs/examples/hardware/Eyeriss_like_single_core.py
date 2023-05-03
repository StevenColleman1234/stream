from inputs.examples.hardware.cores.Eyeriss_like import get_core
from zigzag.classes.hardware.architecture.accelerator import Accelerator

cores = {get_core()}
global_buffer = None
accelerator = Accelerator("Eyeriss-like-single-core", cores, global_buffer)