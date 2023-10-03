# code_analysis



## How to use tools in code analysis 

### 1. Run `function_tag.py`
Use `python function_tag --codedir code_folder`
to tag the inputs, outputs variable names and function names of the Matlab function script(.m) in *code_folder*, and generates a json file as output.

### 2. Run `function_call_analysis.py`
Use `python function_call_analysis --codedir code_path --jsontag tracked_subfunc --visualize vis_way` to analyze the call pattern of a Matlab function *code_path*. Json file *tracked_subfunc* specifies the attributes of the sub-functions tagged by `function_tag.py`.

The input function is a root function, and other called functions in  *tracked_subfunc* are recursively traversed. The function call pattern is generated in json format.

Feel free to visualize the call pattern in different ways specified by `--visualize`
- `--visualize=0`: not visualize
- `--visualize=1`: function call
- `--visualize=2`: function call with parameters passed to child node
- `--visualize=3`: function call with parameters propagation both to child and parent nodes

### 3. Run `save_vars_matlab.py`
Use `python save_vars_maltab.py --call_pattern pattern.json --codedir code_dir --newdir new_code_dir` to generate .m file with variables saving code.

Files in *code_dir* would be copied to new_code_dir if none of its internal variables are needed for other functions' computation analyzed by *pattern.json*. Otherwise, new Matlab scripts will be automatically generated from the original code. These new scripts will include additional logic for saving the required variables."