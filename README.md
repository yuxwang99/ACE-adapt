# ACE-adapt

## What does ACE-adapt do
ACE processes a feature extraction codebase that extracts features based on a one-hot label mask. Each bit in the mask determines whether to extract the corresponding feature.

ACE automatically generates a new codebase that buffers data if it is possible to be reused in other feature subsets.
    

## Use ACE-adapt to optimize runtime efficiency of your biomedical apps
### 0. Install prerequisite packages

- `pip install parse`
- `sudo apt-get install graphviz` (not required if don't need to visualize the call graph)

### 1. Run `function_tag.py`
Use `python function_tag --codedir code_folder`
to tag the inputs, outputs variable names and function names of the Matlab function script(.m) in *code_folder*, and generates a json file as output.

We only edit user-define functions. Hence, we first tag user-define function declaration to get their names, inputs, and outputs to distinguish the same the user-define function invocation between matrix slice. The generated json file indicates the what function should be processed in the following steps.

### 2. Run `function_call_analysis.py`
Use `python function_call_analysis.py` to generate call graoh of the code base, which is saved in json format.

You need to specify 

- rootfile: root function of the feature extraction code base.
- jsontag: filepath of the json file generated from the first step

For more information please refer `python function_call_analysis -h`

Feel free to visualize the call graph in different ways specified by `--visualize`
- `--visualize=0`: not visualize
- `--visualize=1`: visualize in simplify mode (DAG).
- `--visualize=2`: visualize function invocation with function name notated

### 3. Run `save_vars_matlab.py`
Use `python save_vars_maltab.py` to generate .m file with variables saving code.

Files in *code_dir* would be copied to new_code_dir if none of its internal variables are needed for other functions' computation analyzed by *pattern.json*. Otherwise, new Matlab scripts will be automatically generated from the original code. These new scripts will include additional logic for saving the required variables."

## Toy example
Try runing 
`sh sh_toy.sh` to play with the toy_example codebase with ACE-adapt. 
