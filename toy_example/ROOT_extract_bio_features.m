function feats = ROOT_extract_bio_features(signal, mask)

time_domain_feat = compute_time_domain_feats(signal, mask(1:3));

freq_signal = fft(signal);
filter_sig = filter_input(freq_signal);
freq_domain_feat = compute_freq_domain_feats(filter_sig, mask(4:5));

feats = [time_domain_feat, freq_domain_feat];
    
end