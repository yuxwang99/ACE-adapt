function feats = ROOT_extract_bio_features(signal, mask)
global ctrl_vec;
global filter_sig;

time_domain_feat = compute_time_domain_feats(signal, mask(1:3));

freq_signal = fft(signal);
if ctrl_vec(get_var_index('filter_sig'))
    filter_sig = filter_input(freq_signal);
    ctrl_vec(get_var_index('filter_sig'))=0;
end
freq_domain_feat = compute_freq_domain_feats(filter_sig, mask(4:5));

feats = [time_domain_feat, freq_domain_feat];
    
end
