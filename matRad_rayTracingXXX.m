function [inputCube, outputCube] = matRad_rayTracingXXX(ct_cube,dose_cube, ctres,isoCenter,resolution,gantryAngle,couchAngle, imsize, depth)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% matRad visualization of two-dimensional dose distributions on ct including
% segmentation
% 
% call
%   [radDepthV,geoDistV] = matRad_rayTracing(stf,ct,V,rot_coordsV,lateralCutoff)
%
% input
%   stf:           matRad steering information struct of one beam
%   ct:            ct cube
%   V:             linear voxel indices e.g. of voxels inside patient.
%   rot_coordsV    coordinates in beams eye view inside the patient
%   lateralCutoff: lateral cut off used for ray tracing

%
% output
%   radDepthV:  radiological depth inside the patient
%   geoDistV:   optional: geometrical distance inside the patient
%
% References
%   [1] http://www.sciencedirect.com/science/article/pii/S1120179711001359
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% Copyright 2015 the matRad development team. 
% 
% This file is part of the matRad project. It is subject to the license 
% terms in the LICENSE file found in the top-level directory of this 
% distribution and at https://github.com/e0404/matRad/LICENSES.txt. No part 
% of the matRad project, including this file, may be copied, modified, 
% propagated, or distributed except according to the terms contained in the 
% LICENSE file.
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

SAD = 10000;

[gridX,gridZ] = meshgrid(2 * resolution * [-floor(imsize/2):floor(imsize/2)]);

% set up ray matrix
rayMx_bev = [gridX(:) ...
             SAD*ones(numel(gridX),1) ...  
             gridZ(:)];

% Rotation matrix. Transposed because of row vectors
rotMat_vectors_T = transpose(matRad_getRotationMatrix(gantryAngle,couchAngle));

% rotate ray matrix from bev to world coordinates
rayMx_world = rayMx_bev * rotMat_vectors_T;

% compute source ppoint for raz tracing in world coordinates
sourcePoint = [0 -SAD 0] * rotMat_vectors_T;

regGridQueryPoints = 0.9*SAD:resolution:1.1*SAD;

inputCube_padded = NaN * ones(imsize,imsize,numel(regGridQueryPoints));
outputCube_padded = NaN * ones(imsize,imsize,numel(regGridQueryPoints));

firstNonZero = inf;
% perform ray tracing over all rays
% a = zeros(size(rayMx_world,1),1);
for i = 1:size(rayMx_world,1)

% run siddon ray tracing algorithm
[alpha,l,rho,d12,ixHitVoxel] = matRad_siddonRayTracer(isoCenter, ...
                            ctres, ...
                            sourcePoint, ...
                            rayMx_world(i,:), ...
                            ct_cube);
                            
alphaMid = (alpha(1:end-1)+alpha(2:end))/2;                        
alphaMidPhys = [min(regGridQueryPoints) alphaMid*d12 max(regGridQueryPoints)];
ctDensOnRegGrid = interp1(alphaMidPhys,[0 rho{1} 0],regGridQueryPoints,'pchip');

firstNonZero = min(firstNonZero,find(ctDensOnRegGrid>0,1,'first'));


% mask = ctDensOnRegGrid ~= 0;
% tmp = ctDensOnRegGrid(mask);
% % % a(i) = size(tmp, 2);
% tmp = tmp(1:depth);

[cordX,cordZ] = ind2sub([imsize, imsize], i);
% cordX = imsize - cordX + 1;


inputCube_padded(cordZ,cordX,:) = ctDensOnRegGrid;
% inputCube(cordX,cordZ,:) = tmp;

if ~isempty(dose_cube)
    % run siddon ray tracing algorithm
    [alpha,l,rho,d12,ixHitVoxel] = matRad_siddonRayTracer(isoCenter, ...
                                ctres, ...
                                sourcePoint, ...
                                rayMx_world(i,:), ...
                                dose_cube);

    alphaMid = (alpha(1:end-1)+alpha(2:end))/2;                        
    alphaMidPhys = [min(regGridQueryPoints) alphaMid*d12 max(regGridQueryPoints)];
    doseDensOnRegGrid = interp1(alphaMidPhys,[0 rho{1} 0],regGridQueryPoints,'pchip');

    outputCube_padded(cordZ,cordX,:) = doseDensOnRegGrid;
end
if 0%rem(i, 1) == 0
    figure
    hold on
    plot(alphaMidPhys,[0 rho{1} 0],'r')
    plot(regGridQueryPoints,ctDensOnRegGrid,'gx')
    plot(regGridQueryPoints,doseDensOnRegGrid, 'bx')
%     alphaPhys = d12*alpha;
%     intRadDepths = [0 cumsum(rho{1})];
% 
%     alphaPhysInt = [min(regGridQueryPoints) alphaPhys max(regGridQueryPoints)];
%     intRadDepthsInt = [0 intRadDepths intRadDepths(end)];
% 
%     intRadDepthsOnRegGrid = interp1(alphaPhysInt,intRadDepthsInt,regGridQueryPoints,'pchip');

    % figure
%     hold on
%     plot(alphaPhys,intRadDepths,'gx')
    % plot(regGridQueryPoints,intRadDepthsOnRegGrid,'gx')
    title(gantryAngle)
end

end

inputCube = inputCube_padded(:,:,[0:depth-1] + firstNonZero);
if ~isempty(dose_cube)
    outputCube = outputCube_padded(:,:,[0:depth-1] + firstNonZero);
else
    outputCube = []
end



end


