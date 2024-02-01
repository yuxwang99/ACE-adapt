import os
from utils.parser.var_usage_analysis import analyze_var_usage
from utils.parser.expr_class import CallExprAST, VariableExprAST, SliceExprAST
from function_call_analysis import is_sub_func_called
from utils.adapter.gen_matlab_save_code import is_mask_related_func


class VariableSaveStrategy:
    """Class define the variable save strategy"""

    def __init__(self, folder, rootfile, subfolders):
        self.folder = folder
        self.rootfile = rootfile
        self.subfolders = subfolders

    def select_examine_subfuncs(self):
        """Select the sub-functions that need to be examined"""
        raise NotImplementedError("Function selection strategy is not implemented yet")

    def process_examined_subfuncs(self):
        """Select the variables that need to be saved"""
        raise NotImplementedError("Variable saving strategy is not implemented yet")


def is_once_called_func(
    folder_name: str,
    func_dir: str,
    call_pattern: dict,
    parent_func=[],
    reuse_func_list=[],
    sub_folders=[],
):
    # The variable propated to its children function can be regarded as constant if it is
    # produced once under the following conditions:
    # 1. it is not in a loop, or
    # 2. it is in and only in one if clause
    func_called = []
    block_expr, blocks = analyze_var_usage(os.path.join(folder_name, func_dir))

    # Iterate over the block in each file, e.g. function definition.
    for _, var_list in block_expr.items():
        # Iterate over the variables in each block
        for var in var_list:
            # Exclude variables that are not attached in the top level block
            if var.in_loop:
                continue
            for _, expr in var.production.items():
                if not isinstance(expr, CallExprAST) or (
                    not is_sub_func_called(expr.func_name, call_pattern, sub_folders)
                ):
                    continue

                # logic to exclude mask relate function
                if expr.func_name == "calculate_idxs_from_mask":
                    continue

                if expr not in func_called:
                    # check whether the function is called in the same file
                    flag_pre_call = False
                    for pre_call in func_called:
                        if pre_call.func_name == expr.func_name:
                            rep_ind = func_called.index(pre_call)
                            func_called.pop(rep_ind)
                            flag_pre_call = True
                            break
                    if not flag_pre_call:
                        func_called.append(expr)

    # Recursively check the sub-function
    for func in func_called:
        folder = os.path.dirname(func_dir)
        func_name = func.func_name
        if not os.path.isfile(os.path.join(folder, func_name + ".m")):
            func_name = is_sub_func_called(func.func_name, call_pattern, sub_folders)

        if func_name in parent_func:
            reuse_func_list.append(func_name)
        else:
            parent_func.append(func_name)
            parent_func, reuse_func_list = is_once_called_func(
                folder_name,
                func_name + ".m",
                call_pattern,
                parent_func,
                reuse_func_list,
                sub_folders=sub_folders,
            )
    return parent_func, reuse_func_list


def in_use_variable(var, var_list):
    if len(var.usage) != 0:
        return True

    # detect whether brother variables is in use
    for var1 in var_list:
        set1 = set(var1.production.values())
        set2 = set(var.production.values())
        if bool(set1.intersection(set2)):
            if len(var1.usage) != 0:
                return True
    return False


def select_non_loop_used_vars(
    block_expr,
    valid_save_func: list,
    sub_folders: list[str] = [],
):
    save_var_list = []

    for block, var_list in block_expr.items():
        # Exclude variables that are used in the slice expression
        for var in var_list:
            if isinstance(var, SliceExprAST):
                continue
            # Exclude the input variables
            if var._varAttr == 1:
                continue
            # Exclude variables that are not used
            if not in_use_variable(var, var_list):
                continue
            # Exclude variables in the loop
            if var.in_loop:
                continue
            for slice, expr in var.production.items():
                if isinstance(expr, CallExprAST) and is_sub_func_called(
                    expr.func_name, valid_save_func, sub_folders
                ):
                    if is_mask_related_func(expr):
                        continue
                    print("save var: ", var.var_name)
                    save_var_list.append(var)
    return save_var_list


# select which variables to save
def select_top_level_used_vars(
    block_expr,
    top_block,
    valid_save_func: list,
    sub_folders: list[str] = [],
):
    save_var_list = []

    for block, var_list in block_expr.items():
        for var in var_list:
            # Exclude variables that are used in the slice expression
            if isinstance(var, SliceExprAST):
                continue
            # Exclude the input variables
            if var._varAttr == 1:
                continue
            # Exclude variables that are not used
            if len(var.usage) == 0:
                continue
            # Exclude variables that are not attached in the top level block
            if var.get_block() != top_block:
                continue
            if var.in_loop:
                continue
            for slice, expr in var.production.items():
                if isinstance(expr, CallExprAST) and is_sub_func_called(
                    expr.func_name, valid_save_func, sub_folders
                ):
                    # Exclude variables that are generated w.r.t the masks
                    if is_mask_related_func(expr):
                        continue
                    print("save var: ", var.var_name)
                    save_var_list.append(var)
    return save_var_list
