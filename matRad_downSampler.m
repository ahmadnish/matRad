function dd = matRad_downSampler(ct)

downSamplingSize = [3,3,3];

for i = 1:3
    dd.cubeDim(i) = ct.cubeDim(i)/downSamplingSize(i);
end

end