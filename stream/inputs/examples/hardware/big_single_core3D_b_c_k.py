#from classes.hardware.architecture.accelerator import Accelerator
from zigzag.classes.hardware.architecture.core import Core

from inputs.examples.hardware import architecture_definition3D as arch_def
from inputs.examples.hardware import architecture_description3D as arch_des

# def cores():
from inputs.examples.hardware import architecture_definition3D as arch_def
arch_def.size_l2_weights = arch_def.size_l2_weights
arch_def.size_l2_activation = arch_def.size_l2_activation
arch_def.size_l1_weights = arch_def.size_l1_weights
arch_def.size_l1_activation = arch_def.size_l1_activation
arch_def.multiplier_arrary_size = arch_def.multiplier_arrary_size
#
def get_dataflows():
    return [{'D1': ('B', 16), 'D2': ('C', 16), 'D3': ('K', 16)}]

multiplier_array = arch_des.multiplier_array_3D()
memory_hierarchy = arch_des.memory_hierarchy_B_C_K_dataflow(multiplier_array)
dataflows = get_dataflows()
core_1 = Core(0, multiplier_array, memory_hierarchy, dataflows)
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
simd_core = get_simd_core(id=1)
offchip_core_id = 2
offchip_core = get_offchip_core(id=offchip_core_id)

cores_graph = get_2d_mesh([core_1], 1, 1, 64, 0, simd_core=simd_core, offchip_core=offchip_core)

global_buffer = None
accelerator = Accelerator("Big_single_core_b_c_k", cores_graph, global_buffer, offchip_core_id=offchip_core_id)