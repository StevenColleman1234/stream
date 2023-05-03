# This document is used to define the hardware architecture for the thesis of Sebastian Karl.
# 
# There are three different archtiectures considered: a big single core, a homogeneous quadcore
# and a heterogeneous quadcore
# 
###############################################################################################
# 
# The multiplier array of the single core is four times as big as the one of the quadcore
# 
# Size of one dimension in the multiplier array:
multiplier_arrary_size = 1
# 
###############################################################################################
# 
# In the following the size and the read/write bus width of the SRAMs in the architecutres
# are defined. The single core uses directly the size from this file, while the quadcores
# rescale it by a factor of 1/4. The bus width stays the same for all architecutres. The unit
# for the memory sizes are bytes and for the bus width it is bits.
#
# Size L2 SRAM activation:
size_l2_activation = 524288
# Bus width L2 SRAM activation:
width_l2_activation = 8
# Size L1 SRAM activation:
size_l1_activation = 65536/8
# Bus width L1 SRAM activation:
width_l1_activation = 32
# 
###############################################################################################
# 
# In the follwoing the size and read/write bus width of the register files in the
# architectures are defined. The size and width is the same for all three architectures. The
# unit for the memory sizes are bytes and for the bus width it is bits.
# 
# Size register file weights and inputs:
size_rf_weight_input = 1*64
# Bus width register file weights and inputs:
width_rf_weight_input = size_rf_weight_input*8
# Size register file outputs:
size_rf_outputs = 4*32
# Bus width register file outputs:
width_rf_outputs = size_rf_outputs*8
# 
###############################################################################################
# 
# In the following the costs for off chip memory access and the available bus widht is defined.
# 
from zigzag.classes.hardware.architecture.memory_instance import MemoryInstance
off_chip_memory = MemoryInstance(name="dram", size=1073741824*8, r_bw=64, r_port=0, w_port=0, rw_port=1, latency=1, use_cacti_automation=False)
read_costs_off_chip = off_chip_memory.r_cost
size_off_chip = off_chip_memory.size
width_off_chip = off_chip_memory.r_bw

read_write_costs_on_chip = None
read_write_bw_on_chip = None
# 
###############################################################################################
# 
# The core of the quadcore example can communicate over a bus.
# 
# This bus has the following bandwidth:
width_inter_core_bus = 8
# 
###############################################################################################
# 
# The operand in the architecutres have the following bit precision:
operand_precision = 8
# One MAC operations has the following costs (in pJ):
energy_mac_operation = 1.0
# 
###############################################################################################
# 