#from classes.hardware.architecture.accelerator import Accelerator
from zigzag.classes.hardware.architecture.core import Core

from inputs.examples.hardware import quad_architecture_definition as arch_def
from inputs.examples.hardware import quad_architecture_description as arch_des

# def cores():
from inputs.examples.hardware import quad_architecture_definition as arch_def
arch_def.size_l2_weights = arch_def.size_l2_weights
arch_def.size_l2_activation = arch_def.size_l2_activation
arch_def.size_l1_weights = arch_def.size_l1_weights
arch_def.size_l1_activation = arch_def.size_l1_activation
arch_def.multiplier_arrary_size = arch_def.multiplier_arrary_size
#
def get_dataflows():
    return [{'D1': ('C', 4), 'D2': ('C', 4)}]

multiplier_array = arch_des.multiplier_array_2D()
memory_hierarchy = arch_des.memory_hierarchy_C_dataflow(multiplier_array)
dataflows = get_dataflows()
core_1 = Core(0, multiplier_array, memory_hierarchy, dataflows)
core_2 = Core(1, multiplier_array, memory_hierarchy, dataflows)
core_3 = Core(2, multiplier_array, memory_hierarchy, dataflows)
core_4 = Core(3, multiplier_array, memory_hierarchy, dataflows)
#
#     pooling_array = arch_des.pooling_array_3D()
#     memory_hierarchy_pooling = arch_des.memory_hierarchy_pooling(pooling_array)
#     pooling_core = Core(2, pooling_array, memory_hierarchy_pooling)
#     pooling_core.type = "pool"
#
#     return {core_1, pooling_core}
#
#
# cores = cores()
# global_buffer = None
# accelerator = Accelerator("single_core", cores, global_buffer)
# accelerator.core_dataflow_assignment = [3, 6]
#
# a = 1

#from inputs.examples.hardware.cores.Meta_prototype_like import get_core as get_meta_prototype_core
from inputs.examples.hardware.cores.simd import get_core as get_simd_core
from inputs.examples.hardware.cores.offchip import get_offchip_core
from inputs.examples.hardware.nocs.mesh_2d import get_2d_mesh
from stream.classes.hardware.architecture.accelerator import Accelerator

#cores = [get_meta_prototype_core(id,1) for id in range(1)]
simd_core = get_simd_core(id=4)
offchip_core_id = 5
offchip_core = get_offchip_core(id=offchip_core_id)

cores_graph = get_2d_mesh([core_1, core_2, core_3, core_4], 2, 2, 64, 0, simd_core=simd_core, offchip_core=offchip_core)

global_buffer = None
accelerator = Accelerator("Quadcore_c", cores_graph, global_buffer, offchip_core_id=offchip_core_id)
