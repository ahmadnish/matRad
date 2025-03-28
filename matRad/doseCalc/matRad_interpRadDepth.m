function radDepthVcoarse = matRad_interpRadDepth(ct,V,Vcoarse,vXgrid,vYgrid,vZgrid,radDepthV)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% down/up sampling the radiological depth dose cubes
% 
% call
%   radDepthVcoarse = matRad_interpRadDepth(ct,V,Vcoarse,vXgrid,vYgrid,vZgrid,radDepthV)
%
% input
%   ct:             matRad ct structure
%   V:              linear voxel indices of the cst 
%   Vcoarse:        linear voxel indices of the down sampled grid resolution
%   vXgrid:         query points of now location in x dimension
%   vYgrid:         query points of now location in y dimension
%   vZgrid:         query points of now location in z dimension
%   radDepthV:      radiological depth of radDepthIx
%
% output
%   radDepthVcoarse:   interpolated radiological depth of radDepthIx
%
% References
%   -
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%
% Copyright 2018 the matRad development team. 
% 
% This file is part of the matRad project. It is subject to the license 
% terms in the LICENSE file found in the top-level directory of this 
% distribution and at https://github.com/e0404/matRad/LICENSE.md. No part 
% of the matRad project, including this file, may be copied, modified, 
% propagated, or distributed except according to the terms contained in the 
% LICENSE file.
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

matRad_cfg = MatRad_Config.instance();
matRad_cfg.dispDeprecationWarning('This function is obsolete and will be removed in a future release');

for ctScen = 1:ct.numOfCtScen
   radDepthCube             = NaN*ones(ct.cubeDim);
   radDepthCube(V(~isnan(radDepthV{1}))) = radDepthV{ctScen}(~isnan(radDepthV{1}));

   % interpolate cube - cube is now stored in Y X Z 
   coarseRadDepthCube          = matRad_interp3(ct.x,ct.y',ct.z,radDepthCube,vXgrid,vYgrid',vZgrid);
   radDepthVcoarse{ctScen}  = coarseRadDepthCube(Vcoarse);
end

end

