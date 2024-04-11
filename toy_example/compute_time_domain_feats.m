function output = compute_time_domain_feats(x, mask)
output = [];

if mask(1)
    f1 =  feat1(x);
    output = [output, f1];
end

if mask(2)
    f2 = feat2(x);
    output = [output, f2];
end

if mask(3)
    f3 = feat3(x);
    output = [output, f3];
end

end

