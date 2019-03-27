function matRad_rayTracingXXX(ct,isoCenter,resolution,gantryAngle,couchAngle)
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

[gridX,gridZ] = meshgrid(resolution*[-4:4]);

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

% perform ray tracing over all rays
for i = 1:size(rayMx_world,1)

    % run siddon ray tracing algorithm
    [alpha,l,rho,d12,ixHitVoxel] = matRad_siddonRayTracer(isoCenter, ...
                                ct.resolution, ...
                                sourcePoint, ...
                                rayMx_world(i,:), ...
                                ct.cube);
                            
%     alphaMid = (alpha(1:end-1)+alpha(2:end))/2;                        
%     alphaMidPhys = [min(regGridQueryPoints) alphaMid*d12 max(regGridQueryPoints)];
%     ctDensOnRegGrid = interp1(alphaMidPhys,[0 rho{1} 0],regGridQueryPoints,'pchip');
%     
%     figure
%     hold on
%     plot(alphaMidPhys,[0 rho{1} 0],'r')
%     plot(regGridQueryPoints,ctDensOnRegGrid,'gx')

alphaPhys = d12*alpha;
intRadDepths = [0 cumsum(rho{1})];

alphaPhysInt = [min(regGridQueryPoints) alphaPhys max(regGridQueryPoints)];
intRadDepthsInt = [0 intRadDepths intRadDepths(end)];

intRadDepthsOnRegGrid = interp1(alphaPhysInt,intRadDepthsInt,regGridQueryPoints,'pchip');

figure
hold on
plot(alphaPhys,intRadDepths,'r')
plot(regGridQueryPoints,intRadDepthsOnRegGrid,'gx')


end

