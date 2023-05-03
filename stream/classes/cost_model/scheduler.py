from operator import itemgetter
from networkx import DiGraph
from stream.classes.cost_model.memory_manager import MemoryManager
from stream.classes.hardware.architecture.accelerator import Accelerator
from stream.classes.workload.tensor import Tensor


def schedule_graph(G: DiGraph, accelerator: Accelerator, memory_manager: MemoryManager, cores_start_offset=None):
    """Schedule the nodes of graph G across the cores in the system.
    Each node should have a core_allocation and runtime set.

    Args:
        G (DiGraph): Graph containing the nodes to be scheduled.
        accelerator (Accelerator): The accelerator to schedule the nodes on.
        priority (str, optional): Scheduler priority. Can be latency or memory. Defaults to "latency".
        cores_start_offset (dict, optional): A dict containing for each core_id its start offset. Defaults to None.
    """
    # Initialize total link energy cost and memory energy cost
    total_computation_energy_cost = 0
    total_link_energy_cost = 0
    total_memory_energy_cost = 0
    input_onloading_link_energy_cost = 0
    input_onloading_memory_energy_cost = 0
    output_offloading_link_energy_cost = 0
    output_offloading_memory_energy_cost = 0

    all_core_ids = sorted(list(set(n.core_allocation for n in G.nodes())))
    if cores_start_offset is None:
        # Make it 0 for all cores
        cores_start_offset = {core_allocation: 0 for core_allocation in all_core_ids}
    last_node_start_time = {core_allocation: 0 for core_allocation in all_core_ids}
    # cores_memory_usage = {core_id: list() for core_id in all_core_ids}  # init buffer usage at different timesteps

    nb_graph_nodes = G.number_of_nodes()
    nb_scheduled_nodes = 0
    scheduled_nodes = set()

    # List that keeps all possible candidate nodes for each core. Each list item is of the form (preds_end, node)
    # where preds_end is the timestep at which 'node' can at the earliest be scheduled based on its predecessors end timestep
    core_candidates = {core_id: list() for core_id in all_core_ids}

    # Get all the nodes with no predecessors and put them in the candidates queues for the core onto which they are mapped
    source_layers = sorted(set(n.id[0] for n, d in G.in_degree() if d == 0))
    source_layer_nodes = set((n for n in G.nodes() if n.id[0] in source_layers))

    # Put the very first nodes of a layer that doesn't have any incoming edges as the first candidates
    for source_node in (n for n, d in G.in_degree() if d == 0):
        core_allocation = source_node.core_allocation
        core_candidates[core_allocation].append((cores_start_offset[core_allocation], source_node))

    # Get all the nodes with no successors that produce final outputs, used for off-loading final outputs
    sink_layers = sorted(set(n.id[0] for n, d in G.out_degree() if d == 0))
    sink_layer_nodes = set((n for n in G.nodes() if (n.id[0] in sink_layers) and (n.produces_final_output == True)))

    # Get the offchip core id
    offchip_core_id = accelerator.offchip_core_id

    done = False
    # print("STARTING SCHEDULER")
    while not done:
        for core_id, candidates in core_candidates.items():
            # print(memory_manager.stored_cumsum)
            # If this core doesn't have any candidates, continue to the next core
            if not candidates:
                continue
            # Get the best candidate: the one with the earliest possible start time
            (preds_end, best_candidate) = min(candidates)
            # Remove this candidate from the candidates (as we are going to schedule it)
            candidates.remove((preds_end, best_candidate))

            start = cores_start_offset[core_id]  # init start time when the core becomes available

            # Check if this node is a source node: i.e. the inputs need to come from off-chip
            # We don't put the input of the source nodes in the memory manager, as they are discarded right away (every source node is assumed to have unique inputs)
            # All we do is get the latency and energy overhead of the transfers
            # if best_candidate in source_layer_nodes:
            #     input_operand = best_candidate.variable_input_operands[0]
            #     memory_operand = best_candidate.memory_operand_links[input_operand]
            #     if memory_operand not in best_candidate.too_large_operands:
            #         input_tensor = best_candidate.operand_tensors[input_operand]
            #         transfer_start, transfer_end, link_energy_cost, memory_energy_cost = accelerator.transfer_data(input_tensor, offchip_core_id, core_id, memory_operand, 0)  # start transfer as soon as off-chip link is free
            #         # Shift the possible start time of this node if the transfer causes delay
            #         if transfer_end > start:
            #             start = transfer_end
            #         # Add the energy costs to their respective trackers
            #         input_onloading_link_energy_cost += link_energy_cost
            #         input_onloading_memory_energy_cost += memory_energy_cost

            # Get the core corresponding to this core_id
            core = accelerator.get_core(core_id)

            tensors_this_node_needs = []
            ## Step 1
            # Check if for all constant operands (e.g. weight), the highest level of memory of the node processing is one of the core memory levels
            # If it is, we need to fetch the constant tensor if it's not already present on the core
            non_dependent_operands = best_candidate.constant_operands
            constant_tensors = [best_candidate.operand_tensors[op] for op in non_dependent_operands]
            for layer_op, constant_tensor in zip(non_dependent_operands, constant_tensors):
                memory_operand = best_candidate.memory_operand_links[layer_op]
                # Check if this constant operand can be stored on the core for the processing of this node
                if memory_operand not in best_candidate.too_large_operands:  # this constant operand can be stored on the core
                    tensors_this_node_needs.append(constant_tensor)
                    if not memory_manager.contains(constant_tensor, core_id):
                        # Fetch it from off-chip
                        transfer_start, transfer_end, link_energy_cost, memory_energy_cost = accelerator.transfer_data(constant_tensor, offchip_core_id, core_id, memory_operand, -1)  # start transfer as soon as off-chip link is free
                        # Add it to the correct memory
                        memory_manager.add_tensor_to_core(constant_tensor, core_id, transfer_start, constant_tensors, priority=constant_tensor.base_priority)
                        # Shift the possible start time of this node if the transfer causes delay
                        if transfer_end > start:
                            start = transfer_end
                        # Add the energy costs to their respective trackers
                        total_link_energy_cost += link_energy_cost
                        total_memory_energy_cost += memory_energy_cost
                else:
                    # If the constant operand doesn't fit in the top level memory of the core,
                    # we evict all tensors stored in the top level for this memory operand
                    link_energy_cost, memory_energy_cost = memory_manager.evict_all_tensors_from_core(core_id, memory_operand, start, tensors_this_node_needs)
                    total_link_energy_cost += link_energy_cost
                    total_memory_energy_cost += memory_energy_cost

            ## Step 2
            # Check for the non-constant operands (e.g. input activations): if the highest level of memory of the node processing is one of the core memory levels
            # We need to iterate through all the predecessors of this node, and check if we have the outputs of the predecessor present on the core
            for (pred, best_candidate, edge_data) in sorted(G.in_edges(best_candidate, data=True), key=itemgetter(0)):
                # Ignore "predecessor" from same layer
                if pred.id[0] == best_candidate.id[0]:
                    continue
                memory_operand = best_candidate.memory_operand_links[edge_data['operand']]
                if memory_operand not in best_candidate.too_large_operands:  # this pred's output can be stored on the core
                    # Check where the output data of this predecessor is already present on this core
                    pred_output_tensor = pred.operand_tensors[pred.output_operand]
                    tensors_this_node_needs.append(pred_output_tensor)
                    if not memory_manager.contains(pred_output_tensor, core_id):
                        # Transfer the data produced by this predecessor to this candidate's core
                        # First, we check if it is present on the predecessor's core
                        pred_core_id = pred.core_allocation
                        # Calculate the priority value of this predecessor output to be fetched based on the amount of remaining nodes that need this mapped on this core
                        priority = len(set((succ for succ in G.successors(pred) if succ not in scheduled_nodes)))
                        if memory_manager.contains(pred_output_tensor, pred_core_id):
                            # Transfer the tensor from predecessor's core to this core
                            transfer_start, transfer_end, link_energy_cost, memory_energy_cost = accelerator.transfer_data(pred_output_tensor, pred_core_id, core_id, memory_operand, max(pred.end, last_node_start_time[core_id]))
                            # Add tensor to receiver core at start of transfer.
                            memory_manager.add_tensor_to_core(pred_output_tensor, core_id, transfer_start, tensors_this_node_needs, priority=priority)
                            # Decrease the priority of the predecessor's output tensor on the predecessor's core at the end of the transfer
                            memory_manager.update_tensor_priority(pred_output_tensor, pred_core_id, transfer_end, -1)
                            # Add the energy costs to their respective trackers
                            total_link_energy_cost += link_energy_cost
                            total_memory_energy_cost += memory_energy_cost
                            # If this transfer causes stalling in this node's possible start time, update start time
                            start = max(start, transfer_end)
                        # If it's not present on the predecessor's core, we fetch it from off-chip
                        else:
                            # Transfer the tensor from offchip to this node's core
                            transfer_start, transfer_end, link_energy_cost, memory_energy_cost = accelerator.transfer_data(pred_output_tensor, offchip_core_id, core_id, memory_operand, max(pred.end, last_node_start_time[core_id]))
                            # Increase memory usage on receiver core at start of transfer
                            memory_manager.add_tensor_to_core(pred_output_tensor, core_id, transfer_start, tensors_this_node_needs, priority=priority)
                            # We don't decrease the priority, because we assume off-chip is infinite
                            # Add the energy costs to their respective trackers
                            total_link_energy_cost += link_energy_cost
                            total_memory_energy_cost += memory_energy_cost
                            # If this transfer causes stalling in this node's possible start time, update start time
                            start = max(start, transfer_end)
                else:
                    # If the top level memory can't store the tensors required for this memory_operand,
                    # evict them all from the core's top level memory
                    link_energy_cost, memory_energy_cost = memory_manager.evict_all_tensors_from_core(core_id, memory_operand, start, tensors_this_node_needs)
                    start = max(start, pred.end)
                    total_link_energy_cost += link_energy_cost
                    total_memory_energy_cost += memory_energy_cost

            ## Step 3
            # Check if we had any operands that were too large to store in the core's memory, block the relevant off-chip link for the duration
            start = accelerator.block_offchip_links(best_candidate.too_large_operands, core_id, start, best_candidate.get_runtime(), best_candidate.id)
            end = start + best_candidate.get_runtime()
            # If the output tensor can be fully stored in the on-core output memory, add it to the memory manager
            output_operand = best_candidate.output_operand
            memory_operand = best_candidate.memory_operand_links[output_operand]
            output_tensor = best_candidate.operand_tensors[output_operand]
            if memory_operand not in best_candidate.too_large_operands:
                # Memory usage: When the node starts, reserve space for the outputs that will be produced
                memory_manager.add_tensor_to_core(output_tensor, core_id, start, tensors_this_node_needs, priority=output_tensor.base_priority)
                if best_candidate in sink_layer_nodes:  # off-load the outputs to offchip if its a sink node
                    transfer_start, transfer_end, link_energy_cost, memory_energy_cost = accelerator.transfer_data(output_tensor, core_id, offchip_core_id, output_operand, end)
                    output_offloading_link_energy_cost += link_energy_cost
                    output_offloading_memory_energy_cost += memory_energy_cost
                    # Evict the tensor after the transfer is complete as it is a sink layer node output and won't be used by any future nodes
                    memory_manager.update_tensor_priority(output_tensor, core_id, transfer_end, output_tensor.base_priority)
            else:
                # If it can't fit, evict all tensors stored in top level memory of this memory operand
                link_energy_cost, memory_energy_cost = memory_manager.evict_all_tensors_from_core(core_id, memory_operand, start, tensors_this_node_needs)
                total_link_energy_cost += link_energy_cost
                total_memory_energy_cost += memory_energy_cost

            ## Step 4
            # Update the start and end time of the node
            best_candidate.set_start(start)
            best_candidate.set_end(end)
            cores_start_offset[core_id] = end
            last_node_start_time[core_id] = start

            # Add the computation energy of running this node
            total_computation_energy_cost += best_candidate.energy

            # Add this node to the scheduled nodes
            scheduled_nodes.add(best_candidate)

            ## Step 5
            # Memory usage: When the node ends:
            # Decrease the priority of all the tensors this node used
            # This will automatically release the tensor if it is not required by any future nodes
            for tensor_used_by_node in tensors_this_node_needs:
                memory_manager.update_tensor_priority(tensor_used_by_node, core_id, end, -1)

            ## Step 6
            # Memory usage: When the node ends:
            # If this node is a sink node (node that has no successors and that produces a final output), transfer final outputs to offchip
            # if best_candidate in sink_layer_nodes:
            #     transfer_start, transfer_end, link_energy_cost, memory_energy_cost = accelerator.transfer_data(output_tensor, best_candidate_core_id, offchip_core_id, output_operand, end)
            #     output_offloading_link_energy_cost += link_energy_cost
            #     output_offloading_memory_energy_cost += memory_energy_cost

            ## Step 7
            # For each successor of this node, check if all of its predecessors have been scheduled
            for successor in sorted(G.successors(best_candidate)):
                if all((pred in scheduled_nodes for pred in G.predecessors(successor))):
                    preds_end = max((predecessor.end for predecessor in G.predecessors(successor)), default=0)
                    core_candidates[successor.core_allocation].append((preds_end, successor))

            # Increment the number of scheduled nodes
            nb_scheduled_nodes += 1
        done = nb_scheduled_nodes == nb_graph_nodes

    latency = max((n.end for n in G.nodes()))
    # print("Scheduling completed")
    # print(f"Latency found = {latency}")
    return latency, total_computation_energy_cost, total_memory_energy_cost, total_link_energy_cost, input_onloading_link_energy_cost, input_onloading_memory_energy_cost, output_offloading_link_energy_cost, output_offloading_memory_energy_cost
