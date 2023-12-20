# - save_vars_matlab.py - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
# - Generate matlab variable save and load code - - - - - - - - - - - - - - - - - - - - #
import os
from utils.parser.var_usage_analysis import analyze_var_usage
from utils.adapter.save_strategy import (
    is_once_called_func,
    select_non_loop_used_vars,
    VariableSaveStrategy,
)
from utils.adapter.gen_matlab_save_code import save_vars_in_matlab


class VarSave_EmotionalClassification(VariableSaveStrategy):
    def __init__(self, folder, rootfile, subfolders, call_pattern):
        super().__init__(folder, rootfile, subfolders)
        self.call_pattern = call_pattern

    def select_examine_subfuncs(self):
        """Select the sub-functions that need to be examined"""

        process_func_list, reuse_func_list = is_once_called_func(
            self.folder,
            self.rootfile + ".m",
            self.call_pattern,
            [self.rootfile],
            reuse_func_list=[],
            sub_folders=self.subfolders,
        )

        self.process_func = process_func_list

    def process_examined_subfuncs(self, system_func_list=[]):
        for func in self.process_func:
            # save variables computed by the system function which takes on large overhead
            save_var_list = self.select_save_vars(func, system_func_list)
            self.generate_save_code(func, save_var_list)

    def select_save_vars(self, func, system_func_list):
        print("====", func)
        block, _ = analyze_var_usage(os.path.join(self.folder, func + ".m"))

        save_var_list = select_non_loop_used_vars(
            block,
            valid_save_func=self.process_func + system_func_list,
            sub_folders=sub_folders,
        )
        return save_var_list

    def generate_save_code(self, func, save_var_list, relate_save_path="cache"):
        """Generate the code to save the variables"""
        if len(save_var_list) == 0:
            return

        save_cmd = save_vars_in_matlab(
            os.path.join(self.folder, func + ".m"), save_var_list, relate_save_path
        )

        # save the matlab code
        gen_code = open(os.path.join(new_code_dir, func + ".m"), "wt")
        gen_code.write(save_cmd)
        gen_code.close()


if __name__ == "__main__":
    import argparse
    import os
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--codedir", required=True, help="Path to the code directory")
    parser.add_argument(
        "--newcodedir", required=True, help="Path to the new code directory"
    )
    parser.add_argument(
        "--rootfunc", required=True, help="Function name of the root file"
    )
    parser.add_argument(
        "--callpat", required=True, help="Json file of the call pattern"
    )
    parser.add_argument(
        "--subfolder",
        required=False,
        default=[],
        action="append",
        help="Relative path to the sub folders in the code directory",
    )
    args = parser.parse_args()
    code_dir = args.codedir
    new_code_dir = args.newcodedir
    sub_folders = args.subfolder
    func_call = args.rootfunc
    callpat = args.callpat

    with open(callpat, "r") as file:
        call_pattern = json.load(file)

    # create the new folder
    if os.path.isdir(new_code_dir):
        os.system("rm -rf {}".format(new_code_dir))

    os.system("mkdir {}".format(new_code_dir))

    # first copy all .m file to the new folder
    for file_dir in os.listdir(code_dir):
        if os.path.isfile(os.path.join(code_dir, file_dir)):
            if not file_dir.endswith(".m"):
                continue
            # copy the file to the new folders
            os.system(
                "cp {} {}".format(
                    os.path.join(code_dir, file_dir),
                    os.path.join(new_code_dir, file_dir),
                )
            )
        if os.path.isdir(os.path.join(code_dir, file_dir)):
            # copy the sub-folder to the new folders
            os.system(
                "cp -r {} {}".format(
                    os.path.join(code_dir, file_dir),
                    os.path.join(new_code_dir, file_dir),
                )
            )

    strategy = VarSave_EmotionalClassification(
        code_dir, func_call, sub_folders, call_pattern
    )
    strategy.select_examine_subfuncs()
    strategy.process_examined_subfuncs(["plomb"])
