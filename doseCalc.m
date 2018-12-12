function [ct, cst, pln, stf, resultGUI] = doseCalc(ct, cst, vars)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% takes the vars as the variables regarding the slab and does the dose
% calculations
%
%   call:
%         [ct, cst, pln, stf, resultGUI] = slabgeometry(ct, cst, vars)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

pln.radiationMode = 'protons';
pln.machine = 'generic_TOPAS_cropped';

%%
% setting up the plan
pln.numOfFractions        = 30;
pln.propStf.gantryAngles  = vars.gantryAngle;
pln.propStf.couchAngles   = vars.couchAngle;
pln.propStf.bixelWidth    = 150;
pln.propStf.longitudinalSpotSpacing = 150;
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
slab_loc = pln.propStf.isoCenter; 

% turning it into voxels and aligning it
slab_loc(1) = floor(slab_loc(1)/ct.resolution.y) + alignment(1);
slab_loc(2) = floor(slab_loc(2)/ct.resolution.x) + alignment(2);
slab_loc(3) = floor(slab_loc(3)/ct.resolution.z) + alignment(3);

% book keeping the slab location
vars.slab_loc = slab_loc;
% bulding the mask for where the slab is
mask = slabGeometry(vars, ct.cubeDim);

% assigning electron density to the slab
ct.cube{1}(mask == 1) = vars.slab_ed;
ct.cubeHU{1}(mask == 1) = vars.slab_hu;

stf = matRad_generateStf(ct, cst, pln);
stf.ray.energy = vars.Energy;

dij = matRad_calcParticleDose(ct,stf,pln,cst);

resultGUI = matRad_fluenceOptimization(dij,cst,pln);

end
