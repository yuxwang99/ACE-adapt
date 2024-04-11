function output = compute_time_domain_feats(x, mask)
global ctrl_vec;
global f1;
global f2;
global f3;
output = [];

if mask(1)
if ctrl_vec(get_var_index('f1'))
        f1 =  feat1(x);
    ctrl_vec(get_var_index('f1'))=0;
end
    output = [output, f1];
end

if mask(2)
if ctrl_vec(get_var_index('f2'))
        f2 = feat2(x);
    ctrl_vec(get_var_index('f2'))=0;
end
    output = [output, f2];
end

if mask(3)
if ctrl_vec(get_var_index('f3'))
        f3 = feat3(x);
    ctrl_vec(get_var_index('f3'))=0;
end
    output = [output, f3];
end

end


