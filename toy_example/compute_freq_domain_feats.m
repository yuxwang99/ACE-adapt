function output  = compute_freq_domain_feats(x,mask)
output = [];
y = sqrt(x.*conj(x));
if mask(1)
    f4 = feat4(y);
    output = [output, f4];
end

if mask(2)
    f5 = feat5(y);
    output = [output, f5];
end

end

