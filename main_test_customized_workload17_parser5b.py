from zigzag.classes.stages import *
from stream.classes.stages import *
import re

# Initialize the logger
import logging as _logging
_logging_level = _logging.INFO
_logging_format = '%(asctime)s - %(name)s.%(funcName)s +%(lineno)s - %(levelname)s - %(message)s'
_logging.basicConfig(level=_logging_level,
                     format=_logging_format)

#################################
nb_mappings = 243

accelerator = 'inputs.examples.hardware.big_single_core_b_c'
workload_path = "model17a.onnx"
mapping_path = 'inputs.examples.mapping.big_single_core_b_c'

for mapping in range(1, nb_mappings + 1):
    if (mapping == 244):
        hint_loops = []
        CN_define_mode = []
    else:
        hint_loops = "hardcoded" + str(mapping)
        CN_define_mode = "hardcoded" + str(mapping)
    hw_name = accelerator.split(".")[-1]
    wl_name = re.split(r"/|\.", workload_path)[-1]
    experiment_id = f"{hw_name}-{wl_name}-CNmode_{CN_define_mode}-hintloop_{str(hint_loops)}"
    node_hw_cost_pkl_name = f'saved_CN_HW{str(17000 + mapping)}_cost-{experiment_id}'
    plot_file_name = f'-{experiment_id}-'

    mainstage = MainStage([  # Initializes the MainStage as entry point
        AcceleratorParserStage,  # Parses the accelerator
        StreamONNXModelParserStage,  # Parses the ONNX Model into the workload
        # UserDefinedModelParserStage,  # Parses the user-defined Model into the workload
        GenerateCNWorkloadStageNew,
        IntraCoreMappingStage,
        InterCoreMappingStage,
    ],

        accelerator=accelerator,  # required by AcceleratorParserStage
        workload_path=workload_path,  # required by ModelParserStage
        mapping_path=mapping_path,  # required by ModelParserStage
        loma_lpf_limit=6,  # required by LomaStage
        nb_ga_individuals=128,  # number of individuals in each genetic algorithm generation
        nb_ga_generations=5,  # number of genetic algorithm generations
        node_hw_performances_path=f"outputs/{node_hw_cost_pkl_name}.pickle",
        # saved node_hw_performances to skip re-computation
        plot_hof=True,
        # Save schedule and memory usage plot of each individual in the Genetic Algorithm hall of fame
        plot_file_name=plot_file_name,
        CN_define_mode=CN_define_mode,
        hint_loops=hint_loops,
    )

    # Launch the MainStage
    mainstage.run()
