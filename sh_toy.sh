python function_tag.py --codedir toy_example --subdir compute_features --outdir toy_tag.json

python function_call_analysis.py \
    --codedir toy_example --subfolder compute_features \
    --rootfile ROOT_extract_bio_features  --jsontag toy_tag.json \
    --outdir toy_DAG.json --visualize 2

python save_vars_matlab.py \
    --codedir toy_example --newcodedir toy_example_new \
    --rootfunc ROOT_extract_bio_features --callgraph toy_DAG.json \
    --subfolder compute_features