function [ct, cst, pln, stf, resultGUI, mask] = doseCalc(vars)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% takes the vars as the variables regarding the slab and does the dose
% calculations
%
%   call:
%         [ct, cst, pln, stf, resultGUI] = slabgeometry(ct, cst, vars)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

pln.radiationMode = 'protons';
pln.machine = 'generic_TOPAS_cropped';

%% ct and cst
[ct, cst] = makeBoxphantom(vars.boxSize, vars.res);
mask_zeros = zeros(ct.cubeDim);
mask_zeros(ct.cube{1} == 0) = 1;
%%
% setting up the plan
pln.numOfFractions        = 30;
pln.propStf.gantryAngles  = vars.gantryAngle;
pln.propStf.couchAngles   = vars.couchAngle;
pln.propStf.bixelWidth    = 150;
pln.propStf.longitudinalSpotSpacing = 1500;
pln.propStf.numOfBeams    = numel(pln.propStf.gantryAngles);
pln.propStf.isoCenter     = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);
pln.propOpt.runDAO        = 0;
pln.propOpt.runSequencing = 0;

% slab geometry and alignment
alignment = vars.alignment;

% setting up dose with realistic numbers considering it's one bixel and
% only one fraction
cst{1,6}.dose = .2;
cst{2,6}.dose = .5; % 0.0167 each fraction

pln.propOpt.bioOptimization = 'none';

% reading the isocenter
isoCenter = pln.propStf.isoCenter; 

isoCenter(1) = floor(isoCenter(1)/ct.resolution.y);
isoCenter(2) = floor(isoCenter(2)/ct.resolution.x);
isoCenter(3) = floor(isoCenter(3)/ct.resolution.z);
% turning it into voxels and aligning it

slab_loc = isoCenter + alignment;

% book keeping the slab location
vars.slab_loc = slab_loc;
% bulding the mask for where the slab is
mask = slabGeometry(vars, ct.cubeDim);

% assigning electron density to the slab
ct.cube{1}(mask == 1) = vars.slab_sp;
ct.cube{1}(mask_zeros == 1) = 0;
ct = matRad_electronDensitiesToHU(ct);

% mask2 = zeros(ct.cubeDim);
% mask2(isoCenter(1)-79:isoCenter(1)+80, ...
%      isoCenter(2)-14:isoCenter(2)+14, ...
%      isoCenter(3)-14:isoCenter(3)+14) = 1;
 
% ct.cube{1}(mask ~= 1 & mask2 == 1) = ct.cube{1}(mask ~= 1 & mask2 == 1) + .7;

% stf = matRad_generateStf(ct, cst, pln);
% stf.ray.energy = vars.Energy;

load stf.mat

dij = matRad_calcParticleDose(ct,stf,pln,cst);

resultGUI = matRad_fluenceOptimization(dij,cst,pln);

end
