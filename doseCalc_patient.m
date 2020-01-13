function [ct, cst, pln, dij, stf, resultGUI] = doseCalc_patient(vars, ct, cst)
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% takes the vars as the variables regarding the slab and does the dose
% calculations
%
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

pln.radiationMode = 'protons';
pln.machine = 'generic_TOPAS_cropped';

%%
% setting up the plan
pln.numOfFractions        = 30;
pln.propStf.gantryAngles  = vars.gantryAngle;
pln.propStf.couchAngles   = 0;
pln.propStf.bixelWidth    = 1500;
pln.propStf.longitudinalSpotSpacing = 1500;
pln.propStf.numOfBeams    = numel(pln.propStf.gantryAngles);
pln.propStf.isoCenter     = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);
% pln.propStf.isoCenter(3)     = 312;
pln.propStf.isoCenter(3)  = pln.propStf.isoCenter(3) + vars.shift;
pln.propOpt.runDAO        = 0;
pln.propOpt.runSequencing = 0;

pln.propOpt.bioOptimization = 'none';

stf = matRad_generateStf(ct,cst,pln);
stf.ray.energy = vars.energy;

dij = matRad_calcParticleDose(ct,stf,pln,cst);

resultGUI = matRad_fluenceOptimization(dij,cst,pln);


end
