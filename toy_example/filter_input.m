function y = filter_input(x)
a = [2,3];
b = [0.1, 0.2];
y = filter(a, b, x);
end