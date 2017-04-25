"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import nbformat

def get_diff_at_indices(indices, action_data, dest_fname,
                        compare_outputs = False):
    """
    look for diff at particular indices

    indices: (list) cell indices to compare
    action_data: (dict) new notebook data to compare
    dest_fname: (str) name of file to compare to
    compare_outputs: (bool) compare cell outputs
    """

    diff = {}

    # if there is no prior notebook to compare to, we cannot generate a diff
    if not os.path.isfile(dest_fname):
        return diff

    prior_nb = nbformat.read(dest_fname, nbformat.NO_CONVERT)['cells']
    current_nb = action_data['model']['cells']

    # for all other action types
    for i in indices:
        # compare source
        if i >= len(current_nb):
            break # don't compare cells that don't exist
        if i >= len(prior_nb):
            diff[i] = current_nb[i]
        elif (prior_nb[i]["cell_type"] != current_nb[i]["cell_type"]
            or prior_nb[i]["source"] != current_nb[i]["source"]): # its a new cell at the end of the nb
                diff[i] = current_nb[i]
        # compare outputs
        elif compare_outputs and current_nb[i]["cell_type"] == "code":
            prior_outputs = prior_nb[i]['outputs']
            current_outputs = current_nb[i]['outputs']

            if len(prior_outputs) != len(current_outputs):
                diff[i] = current_nb[i]
            else:
                for j in range(len(current_outputs)):
                    # check that the output type matches
                    if prior_outputs[j]['output_type'] != current_outputs[j]['output_type']:
                        diff[i] = current_nb[i]
                    # and that the relevant data matches
                    elif ((prior_outputs[j]['output_type'] in ["display_data","execute_result"]
                        and prior_outputs[j]['data'] != current_outputs[j]['data'])
                        or (prior_outputs[j]['output_type'] == "stream"
                        and prior_outputs[j]['text'] != current_outputs[j]['text'])
                        or (prior_outputs[j]['output_type'] == "error"
                        and prior_outputs[j]['evalue'] != current_outputs[j]['evalue'])):
                            diff[i] = current_nb[i]
    return diff

def indices_to_check(action, selected_index, selected_indices, len_current, len_prior):
    """
    Identify which notebook cells may have changed based on the type of action

    action: (str) action name
    selected_index: (int) single selected cell
    selected_indices: (list of ints) all selected cells
    len_current: (int) length in cells of the notebook we are comparing
    """

    # actions that apply to all selected cells
    if action in['run-cell', 'clear-cell-output', 'change-cell-to-markdown', 
                'change-cell-to-code', 'change-cell-to-raw', 
                'copy-cell', 'cut-cell',
                'toggle-cell-output-collapsed', 'toggle-cell-output-scrolled']:
        return [x for x in selected_indices]
        
    # actions that apply to all selected cells, and the next one
    elif action in ['run-cell-and-insert-below','run-cell-and-select-next']:
        ind = [x for x in selected_indices]
        ind.append(selected_indices[-1] + 1)
        return ind
    
    # actions that apply to the cell before or after first or last selected cell
    elif action in ['insert-cell-above']:
        return [selected_indices[0]]       
    elif action in ['insert-cell-below']:
        return [selected_indices[-1] + 1]
         
    # actions that may insert multiple cells
    elif action in ['paste-cell-above']:
        start = selected_indices[0] # first cell in selection
        num_inserted = len_current - len_prior  
        return [x for x in range(start, start + num_inserted)] 
    elif action in ['paste-cell-below']:
        start = selected_indices[-1] + 1 # first cell after last selected
        num_inserted = len_current - len_prior
        return [x for x in range(start, start + num_inserted)]    
    elif action in ['paste-cell-replace']:     
        start = selected_indices[0] # first cell in selelction
        num_inserted = len_current - len_prior + len(selected_indices)
        return [x for x in range(start, start + num_inserted)]
    
    # actions to move groups of cells up and down
    elif action in ['move-cell-down']:
        if selected_indices[-1] < len_current-1:
            ind = [x for x in selected_indices]
            ind.append(selected_indices[-1] + 1)
            return ind
        else:
            return []
    elif action in ['move-cell-up']:
        if selected_index == 0:
            return []
        else:
            ind = [x for x in selected_indices]
            ind.append(selected_indices[0] - 1)
            return ind
    
    # split, merege, and selection
    elif action in ['merge-cell-with-next-cell', 'unselect-cell']:
        return [selected_index]        
    elif action in ['merge-cell-with-previous-cell']:
        return [max([0, selected_index-1])]
    elif action in ['merge-selected-cells','merge-cells']:
        return min(selected_indices)
    elif action in ['split-cell-at-cursor']:
        return [selected_indices[0], selected_index + 1]
            
    # actions applied to all cells in the notebook, or that could affect all cells
    elif action in ['run-all-cells','restart-kernel-and-clear-output',
                    'confirm-restart-kernel-and-run-all-cells', 
                    'undo-cell-deletion']:
        return [x for x in range(len_current)]
    
    # actions applied to all cells above or below the selected one    
    elif action in ['run-all-cells-above']:
        return [x for x in range(selected_index)]
    elif action in ['run-all-cells-below']:
        return [x for x in range(selected_index, len_current)]

    # remaining acitons such as delete-cell, cut-cell
    else: 
        return []
