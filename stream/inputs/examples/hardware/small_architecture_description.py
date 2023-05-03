from zigzag.classes.hardware.architecture.memory_hierarchy import MemoryHierarchy
from zigzag.classes.hardware.architecture.memory_level import MemoryLevel
from zigzag.classes.hardware.architecture.operational_unit import Multiplier
from zigzag.classes.hardware.architecture.operational_array import MultiplierArray
from zigzag.classes.hardware.architecture.memory_instance import MemoryInstance

from inputs.examples.hardware import small_architecture_definition as arch_def
import zigzag.classes.opt.settings_edp as stream_settings

def memory_hierarchy_OX_FX_FY_dataflow(multiplier_array):
    
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input*8, r_bw=arch_def.width_rf_weight_input, r_port=1, w_port=1, rw_port=0, use_cacti_automation=True)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs*8, r_bw=arch_def.width_rf_outputs, r_port=2, w_port=2, rw_port=0, use_cacti_automation=True)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights*8, r_bw=arch_def.width_l1_weights, r_port=1, w_port=1, rw_port=0, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation*8, r_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=True)
    # Defintion of first SRAM for weights
    l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)

    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824*8, r_bw=arch_def.width_off_chip, r_port=0, w_port=0, rw_port=1, latency=1, use_cacti_automation=True)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_io.r_cost + l2_io.w_cost
        arch_def.read_write_bw_on_chip = l2_io.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        l2_w.size = 1073741824*8
        l2_io.size = 1073741824*8

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions={(0, 1, 0), (0, 0, 1)})
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # Second SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')
    # Second SRAM for inputs and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
                                      served_dimensions='all')
                            
    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                            port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1', 'th': 'rw_port_1'},),
                                            served_dimensions='all')

    return memory_hierarchy_graph

def memory_hierarchy_OX_K_dataflow(multiplier_array):
    
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input*8, r_bw=arch_def.width_rf_weight_input, r_port=1, w_port=1, rw_port=0, use_cacti_automation=True)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs*8, r_bw=arch_def.width_rf_outputs, r_port=2, w_port=2, rw_port=0, use_cacti_automation=True)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights*8, r_bw=arch_def.width_l1_weights, r_port=1, w_port=1, rw_port=0, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation*8, r_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=True)
    # Defintion of first SRAM for weights
    l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)

    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824*8, r_bw=arch_def.width_off_chip, r_port=0, w_port=0, rw_port=1, latency=1, use_cacti_automation=True)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_io.r_cost + l2_io.w_cost
        arch_def.read_write_bw_on_chip = l2_io.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        l2_w.size = 1073741824*8
        l2_io.size = 1073741824*8

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(0, 1)})
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(1, 0)})
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions=set())
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # Second SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')
    # Second SRAM for inputs and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                            port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1', 'th': 'rw_port_1'},),
                                            served_dimensions='all')

    return memory_hierarchy_graph

def memory_hierarchy_B_C_K_dataflow(multiplier_array):
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input * 8,
                           r_bw=arch_def.width_rf_weight_input, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1,
                           rw_port=0, use_cacti_automation=False)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs * 8,
                           r_bw=arch_def.width_rf_outputs, w_bw=arch_def.width_l1_activation, r_port=2, w_port=2,
                           rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights * 8,
                          r_bw=arch_def.width_l1_weights, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1,
                          rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation * 8,
                           r_bw=arch_def.width_l1_activation, w_bw=arch_def.width_l1_activation, r_port=0, w_port=0,
                           rw_port=2, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    # l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    # l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_wio = MemoryInstance(name="l2_wio", mem_type='sram', size=arch_def.size_l2_activation * 8 * 2,
                            r_bw=arch_def.width_l2_activation, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1,
                            rw_port=2, latency=1,
                            use_cacti_automation=False)

    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824 * 8, r_bw=arch_def.width_off_chip,
                              w_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=1, latency=1,
                              use_cacti_automation=False)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_wio.r_cost + l2_wio.w_cost
        arch_def.read_write_bw_on_chip = l2_wio.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        # l2_w.size = 1073741824*8
        # l2_io.size = 1073741824*8
        l2_wio.size = 1073741824 * 8 * 2

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(0, 0, 1)})
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(1, 0, 0)})
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=(
                                      {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions={(0, 1, 0)})
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # # Second SRAM for weights
    # memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
    #                                   port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
    #                                   served_dimensions='all')
    # # Second SRAM for inputs and output
    # memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
    #                                   port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
    #                                               {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
    #                                   served_dimensions='all')

    # Second SRAM for inputs, weights and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_wio, operands=('I1', 'I2', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                          port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1',
                                                       'th': 'rw_port_1'},),
                                          served_dimensions='all')

    # from visualization.graph.memory_hierarchy import visualize_memory_hierarchy_graph
    # visualize_memory_hierarchy_graph(memory_hierarchy_graph)
    return memory_hierarchy_graph

def memory_hierarchy_C_K_dataflow(multiplier_array):
    
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input*8, r_bw=arch_def.width_rf_weight_input, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0, use_cacti_automation=False)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs*8, r_bw=arch_def.width_rf_outputs, w_bw=arch_def.width_l1_activation, r_port=2, w_port=2, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights*8, r_bw=arch_def.width_l1_weights, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation*8, r_bw=arch_def.width_l1_activation, w_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    # l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    # l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_wio = MemoryInstance(name="l2_wio", mem_type='sram', size=arch_def.size_l2_activation * 8 * 2,
                            r_bw=arch_def.width_l2_activation, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=2, latency=1,
                            use_cacti_automation=False)


    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824*8, r_bw=arch_def.width_off_chip, w_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=1, latency=1, use_cacti_automation=False)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_wio.r_cost + l2_wio.w_cost
        arch_def.read_write_bw_on_chip = l2_wio.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        # l2_w.size = 1073741824*8
        # l2_io.size = 1073741824*8
        l2_wio.size = 1073741824 * 8 * 2

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(0, 1)})
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions={(1, 0)})
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # # Second SRAM for weights
    # memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
    #                                   port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
    #                                   served_dimensions='all')
    # # Second SRAM for inputs and output
    # memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
    #                                   port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
    #                                               {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
    #                                   served_dimensions='all')

    # Second SRAM for inputs, weights and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_wio, operands=('I1', 'I2', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                            port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1', 'th': 'rw_port_1'},),
                                            served_dimensions='all')


    #from visualization.graph.memory_hierarchy import visualize_memory_hierarchy_graph
    #visualize_memory_hierarchy_graph(memory_hierarchy_graph)
    return memory_hierarchy_graph


def memory_hierarchy_B_C_dataflow(multiplier_array):
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input * 8,
                           r_bw=arch_def.width_rf_weight_input, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0,
                           use_cacti_automation=False)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs * 8,
                           r_bw=arch_def.width_rf_outputs, w_bw=arch_def.width_l1_activation, r_port=2, w_port=2, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights * 8,
                          r_bw=arch_def.width_l1_weights, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation * 8,
                           r_bw=arch_def.width_l1_activation, w_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    # l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    # l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_wio = MemoryInstance(name="l2_wio", mem_type='sram', size=arch_def.size_l2_activation * 8 * 2,
                            r_bw=arch_def.width_l2_activation, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=2, latency=1,
                            use_cacti_automation=False)


    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824 * 8, r_bw=arch_def.width_off_chip, w_bw=arch_def.width_l1_activation, r_port=0,
                              w_port=0, rw_port=1, latency=1, use_cacti_automation=False)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_wio.r_cost + l2_wio.w_cost
        arch_def.read_write_bw_on_chip = l2_wio.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        # l2_w.size = 1073741824*8
        # l2_io.size = 1073741824*8
        l2_wio.size = 1073741824 * 8 * 2

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(0, 1)})
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=(
                                      {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions={(1, 0)})
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # # Second SRAM for weights
    # memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
    #                                   port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
    #                                   served_dimensions='all')
    # # Second SRAM for inputs and output
    # memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
    #                                   port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
    #                                               {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
    #                                   served_dimensions='all')

    # Second SRAM for inputs, weights and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_wio, operands=('I1', 'I2', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                          port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1',
                                                       'th': 'rw_port_1'},),
                                          served_dimensions='all')

    # from visualization.graph.memory_hierarchy import visualize_memory_hierarchy_graph
    # visualize_memory_hierarchy_graph(memory_hierarchy_graph)
    return memory_hierarchy_graph

def memory_hierarchy_B_K_dataflow(multiplier_array):
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input * 8,
                           r_bw=arch_def.width_rf_weight_input, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0,
                           use_cacti_automation=False)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs * 8,
                           r_bw=arch_def.width_rf_outputs, w_bw=arch_def.width_l1_activation, r_port=2, w_port=2, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights * 8,
                          r_bw=arch_def.width_l1_weights, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation * 8,
                           r_bw=arch_def.width_l1_activation, w_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    # l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    # l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_wio = MemoryInstance(name="l2_wio", mem_type='sram', size=arch_def.size_l2_activation * 8 * 2,
                            r_bw=arch_def.width_l2_activation, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=2, latency=1,
                            use_cacti_automation=False)


    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824 * 8, r_bw=arch_def.width_off_chip, w_bw=arch_def.width_l1_activation, r_port=0,
                              w_port=0, rw_port=1, latency=1, use_cacti_automation=True)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_wio.r_cost + l2_wio.w_cost
        arch_def.read_write_bw_on_chip = l2_wio.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        # l2_w.size = 1073741824*8
        # l2_io.size = 1073741824*8
        l2_wio.size = 1073741824 * 8 * 2

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(1, 0)})
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(0, 1)})
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=(
                                      {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions=set())
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # # Second SRAM for weights
    # memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
    #                                   port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
    #                                   served_dimensions='all')
    # # Second SRAM for inputs and output
    # memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
    #                                   port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
    #                                               {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
    #                                   served_dimensions='all')

    # Second SRAM for inputs, weights and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_wio, operands=('I1', 'I2', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                          port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1',
                                                       'th': 'rw_port_1'},),
                                          served_dimensions='all')

    # from visualization.graph.memory_hierarchy import visualize_memory_hierarchy_graph
    # visualize_memory_hierarchy_graph(memory_hierarchy_graph)
    return memory_hierarchy_graph

def memory_hierarchy_B_dataflow(multiplier_array):
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input * 8,
                           r_bw=arch_def.width_rf_weight_input, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0,
                           use_cacti_automation=False)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs * 8,
                           r_bw=arch_def.width_rf_outputs, w_bw=arch_def.width_l1_activation, r_port=2, w_port=2, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights * 8,
                          r_bw=arch_def.width_l1_weights, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation * 8,
                           r_bw=arch_def.width_l1_activation, w_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    # l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    # l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_wio = MemoryInstance(name="l2_wio", mem_type='sram', size=arch_def.size_l2_activation * 8 * 2,
                            r_bw=arch_def.width_l2_activation, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=2, latency=1,
                            use_cacti_automation=False)


    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824 * 8, r_bw=arch_def.width_off_chip, w_bw=arch_def.width_l1_activation, r_port=0,
                              w_port=0, rw_port=1, latency=1, use_cacti_automation=False)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_wio.r_cost + l2_wio.w_cost
        arch_def.read_write_bw_on_chip = l2_wio.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        # l2_w.size = 1073741824*8
        # l2_io.size = 1073741824*8
        l2_wio.size = 1073741824 * 8 * 2

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(0, 1), (1, 0)})
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=(
                                      {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions=set())
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # # Second SRAM for weights
    # memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
    #                                   port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
    #                                   served_dimensions='all')
    # # Second SRAM for inputs and output
    # memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
    #                                   port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
    #                                               {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
    #                                   served_dimensions='all')

    # Second SRAM for inputs, weights and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_wio, operands=('I1', 'I2', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                          port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1',
                                                       'th': 'rw_port_1'},),
                                          served_dimensions='all')

    # from visualization.graph.memory_hierarchy import visualize_memory_hierarchy_graph
    # visualize_memory_hierarchy_graph(memory_hierarchy_graph)
    return memory_hierarchy_graph

def memory_hierarchy_C_dataflow(multiplier_array):
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input * 8,
                           r_bw=arch_def.width_rf_weight_input, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0,
                           use_cacti_automation=False)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs * 8,
                           r_bw=arch_def.width_rf_outputs, w_bw=arch_def.width_l1_activation, r_port=2, w_port=2, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights * 8,
                          r_bw=arch_def.width_l1_weights, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation * 8,
                           r_bw=arch_def.width_l1_activation, w_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    # l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    # l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_wio = MemoryInstance(name="l2_wio", mem_type='sram', size=arch_def.size_l2_activation * 8 * 2,
                            r_bw=arch_def.width_l2_activation, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=2, latency=1,
                            use_cacti_automation=False)


    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824 * 8, r_bw=arch_def.width_off_chip, w_bw=arch_def.width_l1_activation, r_port=0,
                              w_port=0, rw_port=1, latency=1, use_cacti_automation=True)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_wio.r_cost + l2_wio.w_cost
        arch_def.read_write_bw_on_chip = l2_wio.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        # l2_w.size = 1073741824*8
        # l2_io.size = 1073741824*8
        l2_wio.size = 1073741824 * 8 * 2

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=(
                                      {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions={(0, 1), (1, 0)})
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # # Second SRAM for weights
    # memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
    #                                   port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
    #                                   served_dimensions='all')
    # # Second SRAM for inputs and output
    # memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
    #                                   port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
    #                                               {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
    #                                   served_dimensions='all')

    # Second SRAM for inputs, weights and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_wio, operands=('I1', 'I2', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                          port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1',
                                                       'th': 'rw_port_1'},),
                                          served_dimensions='all')

    # from visualization.graph.memory_hierarchy import visualize_memory_hierarchy_graph
    # visualize_memory_hierarchy_graph(memory_hierarchy_graph)
    return memory_hierarchy_graph

def memory_hierarchy_K_dataflow(multiplier_array):
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input * 8,
                           r_bw=arch_def.width_rf_weight_input, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0,
                           use_cacti_automation=False)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs * 8,
                           r_bw=arch_def.width_rf_outputs, w_bw=arch_def.width_l1_activation, r_port=2, w_port=2, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights * 8,
                          r_bw=arch_def.width_l1_weights, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=0, use_cacti_automation=False)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation * 8,
                           r_bw=arch_def.width_l1_activation, w_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=False)
    # Defintion of first SRAM for weights
    # l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    # l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_wio = MemoryInstance(name="l2_wio", mem_type='sram', size=arch_def.size_l2_activation * 8 * 2,
                            r_bw=arch_def.width_l2_activation, w_bw=arch_def.width_l1_activation, r_port=1, w_port=1, rw_port=2, latency=1,
                            use_cacti_automation=False)


    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824 * 8, r_bw=arch_def.width_off_chip, w_bw=arch_def.width_l1_activation, r_port=0,
                              w_port=0, rw_port=1, latency=1, use_cacti_automation=False)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_wio.r_cost + l2_wio.w_cost
        arch_def.read_write_bw_on_chip = l2_wio.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        # l2_w.size = 1073741824*8
        # l2_io.size = 1073741824*8
        l2_wio.size = 1073741824 * 8 * 2

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions={(0, 1), (1, 0)})
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=(
                                      {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions=set())
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # # Second SRAM for weights
    # memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
    #                                   port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
    #                                   served_dimensions='all')
    # # Second SRAM for inputs and output
    # memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
    #                                   port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
    #                                               {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
    #                                   served_dimensions='all')

    # Second SRAM for inputs, weights and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_wio, operands=('I1', 'I2', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2',
                                                   'th': 'rw_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                          port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                      {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1',
                                                       'th': 'rw_port_1'},),
                                          served_dimensions='all')

    # from visualization.graph.memory_hierarchy import visualize_memory_hierarchy_graph
    # visualize_memory_hierarchy_graph(memory_hierarchy_graph)
    return memory_hierarchy_graph

def memory_hierarchy_default(multiplier_array):
    
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''
    # Defintion of register file for inputs and weights
    rf_1B = MemoryInstance(name="rf_1B", mem_type='rf', size=arch_def.size_rf_weight_input*8, r_bw=arch_def.width_rf_weight_input, r_port=1, w_port=1, rw_port=0, use_cacti_automation=True)
    # Defintion of rRegister file for outputs
    rf_2B = MemoryInstance(name="rf_4B", mem_type='rf', size=arch_def.size_rf_outputs*8, r_bw=arch_def.width_rf_outputs, r_port=2, w_port=2, rw_port=0, use_cacti_automation=True)
    # Defintion of first SRAM for weights
    l1_w = MemoryInstance(name="l1_w", mem_type='sram', size=arch_def.size_l1_weights*8, r_bw=arch_def.width_l1_weights, r_port=1, w_port=1, rw_port=0, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l1_io = MemoryInstance(name="l1_io", mem_type='sram', size=arch_def.size_l1_activation*8, r_bw=arch_def.width_l1_activation, r_port=0, w_port=0, rw_port=2, use_cacti_automation=True)
    # Defintion of first SRAM for weights
    l2_w = MemoryInstance(name="l2_w", mem_type='sram', size=arch_def.size_l2_weights*8, r_bw=arch_def.width_l2_weigths, r_port=1, w_port=1, rw_port=0, latency=1, use_cacti_automation=True)
    # Defintion of first SRAM for inputs and outputs
    l2_io = MemoryInstance(name="l2_io", mem_type='sram', size=arch_def.size_l2_activation*8, r_bw=arch_def.width_l2_activation, r_port=0, w_port=0, rw_port=2, latency=1, use_cacti_automation=True)

    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824*8, r_bw=arch_def.width_off_chip, r_port=0, w_port=0, rw_port=1, latency=1, use_cacti_automation=True)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = l2_io.r_cost + l2_io.w_cost
        arch_def.read_write_bw_on_chip = l2_io.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        l2_w.size = 1073741824*8
        l2_io.size = 1073741824*8

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Register file for input
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I1',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for weight
    memory_hierarchy_graph.add_memory(memory_instance=rf_1B, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions=set())
    # Register file for output
    memory_hierarchy_graph.add_memory(memory_instance=rf_2B, operands=('O',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions=set())
    # First SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l1_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')

    # First SRAM for inputs and outputs
    memory_hierarchy_graph.add_memory(memory_instance=l1_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
                                      served_dimensions='all')
    # Second SRAM for weights
    memory_hierarchy_graph.add_memory(memory_instance=l2_w, operands=('I2',),
                                      port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},),
                                      served_dimensions='all')
    # Second SRAM for inputs and output
    memory_hierarchy_graph.add_memory(memory_instance=l2_io, operands=('I1', 'O'),
                                      port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                  {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_2', 'th': 'rw_port_2'},),
                                      served_dimensions='all')
    
    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                            port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1', 'th': 'rw_port_1'},),
                                            served_dimensions='all')


    return memory_hierarchy_graph


def memory_hierarchy_pooling(multiplier_array):
    
    """Memory hierarchy variables"""
    ''' size=#bit, bw=#bit'''

    # Defintion of first SRAM for inputs and outputs and weights
    sram = MemoryInstance(name="sram", mem_type='sram', size=131072*8, r_bw=512, r_port=2, w_port=2, rw_port=0, use_cacti_automation=True)

    if stream_settings.RUN_LAYER_BY_LAYER:
        dram = MemoryInstance(name="dram", mem_type='dram', size=1073741824*8, r_bw=arch_def.width_off_chip, r_port=0, w_port=0, rw_port=1, latency=1, use_cacti_automation=True)
        arch_def.read_write_costs_on_chip = 1
        arch_def.read_write_bw_on_chip = 1
    else:
        arch_def.read_write_costs_on_chip = sram.r_cost + sram.w_cost
        arch_def.read_write_bw_on_chip = sram.r_bw
        # artifically increase l2 memories to ensure that entire activation and weights of one layer can fit in there // Stream scheduler keeps track if activation buffer and weight buffer is not exeeded
        sram.size = 1073741824*8

    memory_hierarchy_graph = MemoryHierarchy(operational_array=multiplier_array)

    '''
    fh: from high = wr_in_by_high = 
    fl: from low = wr_in_by_low 
    th: to high = rd_out_to_high = 
    tl: to low = rd_out_to_low = 
    '''
    # Second SRAM for inputs and output
    memory_hierarchy_graph.add_memory(memory_instance=sram, operands=('I1', 'I2', 'O'),
                                            port_alloc=({'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'w_port_1', 'tl': 'r_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'w_port_2', 'tl': 'r_port_2', 'fl': 'w_port_2', 'th': 'r_port_2'},),
                                      served_dimensions='all')

    if stream_settings.RUN_LAYER_BY_LAYER:
        # Global DRAM
        memory_hierarchy_graph.add_memory(memory_instance=dram, operands=('I1', 'I2', 'O'),
                                            port_alloc=({'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': None, 'th': None},
                                                        {'fh': 'rw_port_1', 'tl': 'rw_port_1', 'fl': 'rw_port_1', 'th': 'rw_port_1'},),
                                            served_dimensions='all')


    return memory_hierarchy_graph


def multiplier_array_2D():
    """ Multiplier array variables """
    multiplier_input_precision = [arch_def.operand_precision, arch_def.operand_precision]
    multiplier_energy = arch_def.energy_mac_operation
    multiplier_area = 1
    dimensions = {'D1': arch_def.multiplier_arrary_size, 'D2': arch_def.multiplier_arrary_size}

    multiplier = Multiplier(multiplier_input_precision, multiplier_energy, multiplier_area)
    multiplier_array = MultiplierArray(multiplier, dimensions)

    return multiplier_array

def multiplier_array_3D():
    """ Multiplier array variables """
    multiplier_input_precision = [arch_def.operand_precision, arch_def.operand_precision]
    multiplier_energy = arch_def.energy_mac_operation
    multiplier_area = 1 

    if arch_def.multiplier_arrary_size == 32:
        dimensions = {'D1': arch_def.multiplier_arrary_size*2, 'D2': arch_def.multiplier_arrary_size/8, 'D3': arch_def.multiplier_arrary_size/8}
    else: 
        import math
        dimensions = {'D1': math.ceil(arch_def.multiplier_arrary_size*1.74), 'D2': math.ceil(arch_def.multiplier_arrary_size/11), 'D3': math.ceil(arch_def.multiplier_arrary_size/11)}

    multiplier = Multiplier(multiplier_input_precision, multiplier_energy, multiplier_area)
    multiplier_array = MultiplierArray(multiplier, dimensions)

    return multiplier_array

def pooling_array_3D():
    """ Multiplier array variables """
    multiplier_input_precision = [arch_def.operand_precision, arch_def.operand_precision]
    multiplier_energy = arch_def.energy_mac_operation
    multiplier_area = 1 

    dimensions = {'D1': 4, 'D2': 3, 'D3': 3}

    multiplier = Multiplier(multiplier_input_precision, multiplier_energy, multiplier_area)
    multiplier_array = MultiplierArray(multiplier, dimensions)

    return multiplier_array    
