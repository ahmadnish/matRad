% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% matRad script
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

clc, %clear

% meta information for treatment plan
load('AlderNish.mat');
pln.radiationMode   = 'protons';     % either photons / protons / carbon
pln.machine         = 'generic_TOPAS_cropped';

pln.numOfFractions  = 30;

% beam geometry settings
pln.propStf.bixelWidth      = 1500; % [mm] / also corresponds to lateral spot spacing for particles
pln.propStf.longitudinalSpotSpacing = 1500;
pln.propStf.gantryAngles    = [0]; % [?]
pln.propStf.couchAngles     = zeros(size(pln.propStf.gantryAngles));% [?]
pln.propStf.numOfBeams      = numel(pln.propStf.gantryAngles);
pln.propStf.isoCenter       = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);


% optimization settings
pln.propOpt.bioOptimization = 'none'; % none: physical optimization;             const_RBExD; constant RBE of 1.1;
                                      % LEMIV_effect: effect-based optimization; LEMIV_RBExD: optimization of RBE-weighted dose
pln.propOpt.runDAO          = false;  % 1/true: run DAO, 0/false: don't / will be ignored for particles
pln.propOpt.runSequencing   = false;  % 1/true: run sequencing, 0/false: don't / will be ignored for particles and also triggered by runDAO below

stf = matRad_generateStf(ct,cst,pln);

for i=1:size(pln.propStf.gantryAngles,2)
    input_cube= matRad_rayTracingXXX(ct,stf(i).isoCenter,2,stf(i).gantryAngle,stf(i).couchAngle);
end

% dij = matRad_calcParticleDose(ct,stf,pln,cst);
% 
% resultGUI = matRad_fluenceOptimization(dij,cst,pln);