function output  = compute_freq_domain_feats(x,mask)
global ctrl_vec;
global f4;
global f5;
output = [];
y = sqrt(x.*conj(x));
if mask(1)
if ctrl_vec(get_var_index('f4'))
        f4 = feat4(y);
    ctrl_vec(get_var_index('f4'))=0;
end
    output = [output, f4];
end

if mask(2)
if ctrl_vec(get_var_index('f5'))
        f5 = feat5(y);
    ctrl_vec(get_var_index('f5'))=0;
end
    output = [output, f5];
end

end


