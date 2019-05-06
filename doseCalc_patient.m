function [ct, cst, pln, dij, stf, resultGUI] = doseCalc_patient(vars)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% takes the vars as the variables regarding the slab and does the dose
% calculations
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

pln.radiationMode = 'protons';
pln.machine = 'generic_TOPAS_cropped';

%% ct and cst
tmp = load('LungNish.mat');
ct = tmp.ct;
cst = tmp.cst;
clear tmp
%%
% setting up the plan
pln.numOfFractions        = 30;
pln.propStf.gantryAngles  = vars.gantryAngle;
pln.propStf.couchAngles   = 0;
pln.propStf.bixelWidth    = 1500;
pln.propStf.longitudinalSpotSpacing = 1500;
pln.propStf.numOfBeams    = numel(pln.propStf.gantryAngles);
pln.propStf.isoCenter     = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);
pln.propStf.isoCenter(3)  = pln.propStf.isoCenter(3) + vars.shift;
pln.propOpt.runDAO        = 0;
pln.propOpt.runSequencing = 0;


% setting up dose with realistic numbers considering it's one bixel and
% only one fraction
% cst{1,6}.dose = .2;
% cst{2,6}.dose = .5; % 0.0167 each fraction

pln.propOpt.bioOptimization = 'none';

stf = matRad_generateStf(ct,cst,pln);
stf.ray.energy = vars.energy;

% input_cube= matRad_rayTracingXXX(ct.cube, ct.resolution,stf.isoCenter,2,stf.gantryAngle,stf.couchAngle);

dij = matRad_calcParticleDose(ct,stf,pln,cst);

resultGUI = matRad_fluenceOptimization(dij,cst,pln);

end
